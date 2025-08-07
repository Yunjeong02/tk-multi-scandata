
import re
import shutil
from pathlib import Path
from tank.platform.qt import QtCore, QtGui
from ..view.scandata_ui import Ui_Dialog
from ..controller.format_converter import Format_Converter
from collections import defaultdict

SELECT, THUMB, SEQ, SHOT, VER, SCAN, FRANGE, TCODE, COLORSPACE, DATETIME, CAM, UNUSED, MOVIE = range(13)

class ValidationData:
    def __init__(
        self, filepath: Path, start_frame: int, end_frame: int, fps: float,
        version_int: int, src_version: str, shot_name: str, editorial_list
    ):
        self.filepath = filepath
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.fps = fps
        self.version_int = version_int
        self.src_version = src_version
        self.shot_name = shot_name
        self.editorial_list = editorial_list
        
class ValidationResult:
    def __init__(self, name: str):
        self.name = name
        self.errors = []

    def add(self, msg: str):
        self.errors.append(msg)

    @property
    def passed(self) -> bool:
        return not self.errors

class ValidationController(QtCore.QObject):
    def __init__(self, ui: Ui_Dialog  ):
        super().__init__()
        self.ui = ui
        # self.last_open_dir = last_open_dir
        self.ui.table.setColumnHidden(UNUSED, True)
        self._re_ver = re.compile(r"_v(\d{3})")
        self.format_converter = Format_Converter()

        ui.validate_timecode.clicked.connect(self.validate_timecode)
        ui.validate_version.clicked.connect(self.validate_version)
        ui.validate_src_version.clicked.connect(self.validate_src_version)
        ui.validate_editorial.clicked.connect(self.validate_editorial)

    def validate_all(self):
        self._validate_items(["timecode", "version", "src_version", "editorial"])

    def validate_timecode(self):
        self._validate_items(["timecode"])

    def validate_version(self):
        self._validate_items(["version"])

    def validate_src_version(self):
        self._validate_items(["src_version"])

    def validate_editorial(self):
        self._validate_items(["editorial"])

    def _validate_items(self, items_to_check: list[str]):
        rows, errors = self._collect_rows()
        if errors:
            self._show_msg("입력 오류", "\n".join(errors))
            return
        if not rows:
            self._show_msg("안내", "체크된 행이 없습니다.")
            return

        full_log, all_pass = [], True
        for idx, data in enumerate(rows, 1):
            self._current_validating_row = idx - 1
            if not data.filepath or not data.filepath.exists():
                full_log.append(f"Row {idx}: 잘못된 filepath: {data.filepath}")
                all_pass = False
                continue

            results = self._run_checks(data, items_to_check)
            full_log.append(f"── Row {idx} ────────────")
            for res in results:
                head = "O" if res.passed else "X"
                full_log.append(f"[{res.name}] {head}")
                full_log += [f"  - {e}" for e in res.errors]
                if not res.passed:
                    all_pass = False

        self._show_msg("검증 결과", "\n".join(full_log))
        self.ui.publish_button.setEnabled(all_pass)

    def _update_ui_path_field(self, row: int, col: int, text: str):
        item = self.ui.table.item(row, col)
        if item:
            item.setText(text)
        else:
            new_item = QtGui.QTableWidgetItem(text)
            self.ui.table.setItem(row, col, new_item)

    def _update_ui_version_field(self, row: int, version_int: int):
        tbl = self.ui.table
        item = tbl.item(row, VER)
        if item:
            item.setText(f"v{version_int:03d}")

    def _run_checks(self, d: ValidationData, items_to_check: list[str]):
        checks = {
            "timecode": self._check_timecode,
            "version": self._check_version,
            "src_version": self._check_src_version,
            "editorial": self._check_editorial
        }
        return [checks[item](d) for item in items_to_check if item in checks]

    def _get_src_version_from_path(self, path: Path) -> str:
        for p in [path] + list(path.parents):
            if re.fullmatch(r"v\d{3}", p.name):
                return p.name
        return ""

    def _check_timecode(self, d: ValidationData):
        res = ValidationResult("Timecode")
        if d.start_frame != 1:
            res.add(f"Start Frame {d.start_frame} ≠ 1")
        if d.end_frame <= d.start_frame:
            res.add("End Frame이 Start Frame보다 작거나 같습니다.")
        if abs(d.fps - 24.0) > 0.01:
            res.add(f"FPS {d.fps} ≠ 24.0")
        return res

    def _check_version(self, d: ValidationData):
        res = ValidationResult("Version")
        version_root = d.filepath
        print(f"[DEBUG] version_root: {version_root}")

        if not version_root.exists() or not version_root.is_dir():
            res.add(f"버전 폴더 경로가 없습니다: {version_root}")
            return res

        # 버전 폴더 목록 수집
        version_numbers = []
        for p in version_root.iterdir():
            if p.is_dir():
                m = re.fullmatch(r"v(\d{3})", p.name)
                if m:
                    version_numbers.append(int(m.group(1)))

        version_numbers.sort()
        latest_version = version_numbers[-1] if version_numbers else 0
        next_version = latest_version + 1
        current_version = d.version_int

        # 버전 폴더가 하나도 없으면 v001 폴더 생성 및 UI 업데이트
        if latest_version == 0:
            v001_path = version_root / "v001"
            if not v001_path.exists():
                try:
                    v001_path.mkdir(parents=True, exist_ok=True)
                    self._show_msg("버전 자동 생성", "최초 버전 v001 폴더를 생성했습니다.")
                except Exception as e:
                    res.add(f"v001 폴더 생성 실패: {e}")
                    return res
            self._update_ui_version_field(self._current_validating_row, 1)
            return res

        # UI에 입력된 버전이 최신 버전 이하라면 다음 버전 폴더 생성 및 UI 업데이트
        if current_version <= latest_version:
            next_version_path = version_root / f"v{next_version:03d}"
            if not next_version_path.exists():
                try:
                    next_version_path.mkdir(parents=True, exist_ok=True)
                    self._show_msg("버전 자동 생성", f"다음 버전 폴더 v{next_version:03d}를 생성했습니다.")
                except Exception as e:
                    res.add(f"v{next_version:03d} 폴더 생성 실패: {e}")
                    return res
            self._update_ui_version_field(self._current_validating_row, next_version)
            # 버전 경로 저장
            self._update_ui_path_field(self._current_validating_row, UNUSED, str(next_version_path))

        else:
            self._show_msg("버전 검증", f"현재 버전 v{current_version:03d}는 최신 버전 이상입니다.")
            # 최신 이상 버전도 저장
            current_version_path = version_root / f"v{current_version:03d}"
            self._update_ui_path_field(self._current_validating_row, UNUSED, str(current_version_path))

        return res

    def _check_src_version(self, d: ValidationData):
        res = ValidationResult("Src Version")
        expected = f"v{d.version_int:03d}"
        if d.src_version != expected:
            res.add(f"Src 버전 {d.src_version} ≠ 입력 버전 {expected}")
        return res

    def _check_editorial(self, d: ValidationData):
        res = ValidationResult("Editorial")
        if d.shot_name not in d.editorial_list:
            res.add(f"샷 '{d.shot_name}' 편집 리스트에 없음")
        return res

    def _find_seq_root(self, start_path: Path) -> Path:
        for parent in start_path.resolve().parents:
            candidate = parent / "scandata_project" / "seq"
            if candidate.is_dir():
                return candidate
        raise FileNotFoundError("상위 경로에서 'scandata_project/seq'를 찾을 수 없습니다.")
    
    def _collect_rows(self):
        tbl = self.ui.table
        rows, errs = [], []

        def cell(r, c):
            item = tbl.item(r, c)
            return item.text().strip() if item else ""

        for r in range(tbl.rowCount()):
            chk_item = tbl.item(r, SELECT)
            if not chk_item or chk_item.checkState() != QtCore.Qt.Checked:
                continue
            try:
                scan_path_str = cell(r, SCAN)
                if not scan_path_str:
                    errs.append(f"Row {r+1}: Scan 경로 없음")
                    continue
                scan_path = Path(scan_path_str).resolve()

                parts = scan_path.parts
                try:
                    scan_index = parts.index("scan")
                    sp_index = parts.index("scandata_project")
                    base_root = Path(*parts[:sp_index + 1])
                    seq_root = base_root / "seq"
                except ValueError:
                    errs.append(f"Row {r+1}: scan 또는 scandata_project 폴더가 경로에 없습니다.")
                    continue

                frame_range = cell(r, FRANGE)
                start_s, end_s = frame_range.split("-")
                start_f, end_f = int(start_s), int(end_s)
                fps_val = 24.0
                ver_str = cell(r, VER).lstrip("vV")
                ver_int = int(ver_str) if ver_str.isdigit() else 1

                seq_folder = cell(r, SEQ).strip() or "default_seq"
                shot_folder = cell(r, SHOT).strip() or "default_shot"

                version_root = seq_root / seq_folder / shot_folder / "org" / "plate" / "org"

                if not version_root.exists():
                    try:
                        version_root.mkdir(parents=True, exist_ok=True)
                        v001_path = version_root / "v001"
                        v001_path.mkdir(parents=True, exist_ok=True)
                        print(f"[INFO] Row {r+1}: 경로 생성 {version_root} 및 {v001_path}")
                    except Exception as e:
                        errs.append(f"Row {r+1}: 경로 생성 실패 {version_root} - {e}")
                        continue

                src_ver = self._get_src_version_from_path(version_root)
                if not src_ver:
                    src_ver = "v001"
                    print(f"[WARN] Row {r+1}: src_version이 없어 기본 'v001'로 설정")

                data = ValidationData(
                    filepath=version_root,
                    start_frame=start_f,
                    end_frame=end_f,
                    fps=fps_val,
                    version_int=ver_int,
                    src_version=src_ver,
                    shot_name=shot_folder,
                    editorial_list=["SH010", "SH012", "SH013"]
                )
                rows.append(data)

            except Exception as e:
                errs.append(f"Row {r+1}: 파싱 실패 - {e}")
        return rows, errs

    def _show_msg(self, title, text):
        parent = self.ui.table.parent()
        QtGui.QMessageBox.information(parent, title, text)
