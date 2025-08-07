from pathlib import Path
from tank.platform.qt import QtCore, QtGui
from ..model.shotgrid_model import ShotGridModel
from ..controller.format_converter import Format_Converter
from shotgun_api3 import Shotgun
from .validate_controller import UNUSED  # 열 번호 상수 가져오기

# 열 인덱스 정의
SELECT_COL = 0
SHOT_NAME_COL = 3
VERSION_COL = 4
SCAN_PATH_COL = 5
MOVIE_PATH_COL = 12
MP4_PATH_COL = 11
THUMB_PATH_COL = 1  # 썸네일 이미지(QLabel)
SEQ = 2           # 시퀀스 열 번호 (예)
SHOT = 3          # 샷 열 번호 (예)

class ShotGridContext:
    def __init__(self, project_id):
        self.project_id = project_id
        self.shot_versions = {}
        self.shots = {}
        # ShotGrid API 연결 (발급받은 스크립트명과 키로 변경 필요)
        self.sg = Shotgun(
            base_url="https://westworld5.shotgrid.autodesk.com",
            script_name="yunjeong",      # 실제 스크립트명으로 변경
            api_key="ztjyumitOhqarxmvt7kzo~dkh"             # 실제 API키로 변경
        )

    def load_data(self, model: ShotGridModel):
        self.shots.clear()
        for row in model.iter_rows():
            shot_name = row['Shot Name'].strip()
            self.shots[shot_name] = row.to_dict()

    def get_next_version_code(self, shot_name):
        if shot_name not in self.shot_versions:
            self.shot_versions[shot_name] = 0
        self.shot_versions[shot_name] += 1
        return f"v{self.shot_versions[shot_name]:03d}"


    def publish_version(self, seq_name, shot_name, version_code, webm_path: Path,
                    mp4_path: Path = None, thumbnail_path: Path = None, task_type: str = "CMP"):

        print(f"=== Publish Start ===")
        print(f"Project ID: {self.project_id}")
        print(f"Sequence: {seq_name}")
        print(f"Shot: {shot_name}")
        print(f"Version: {version_code}")

        # 1) Sequence 엔티티 조회 (없으면 생성)
        seq_entity = self.sg.find_one(
            "Sequence",
            [["project", "is", {"type": "Project", "id": self.project_id}], ["code", "is", seq_name]],
            ["id"]
        )
        if not seq_entity:
            print(f"[⚠️] Sequence '{seq_name}' not found. Creating new Sequence entity.")
            seq_data = {
                "project": {"type": "Project", "id": self.project_id},
                "code": seq_name,
            }
            seq_entity = self.sg.create("Sequence", seq_data)
            if seq_entity:
                print(f" Created Sequence ID: {seq_entity.get('id')}")
            else:
                print(f" Failed to create Sequence '{seq_name}'. Aborting.")
                return

        # 2) Shot 엔티티 조회 (없으면 생성)
        fields = self.sg.schema_field_read("Shot")
        print(fields.keys())

        shot_entity = self.sg.find_one(
            "Shot",
            [["project", "is", {"type": "Project", "id": self.project_id}],
            ["code", "is", shot_name]],
            ["id"]
        )
        if not shot_entity:
            print(f" Shot '{shot_name}' not found. Creating new Shot entity.")
            shot_data = {
                "project": {"type": "Project", "id": self.project_id},
                "code": shot_name,
                "sg_sequence": {"type": "Sequence", "id": seq_entity["id"]},  # 여기 필드명 수정!
            }
            shot_entity = self.sg.create("Shot", shot_data)

            if shot_entity:
                print(f" Created Shot ID: {shot_entity.get('id')}")
            else:
                print(f" Failed to create Shot '{shot_name}'. Aborting.")
                return

        # 3) Version 생성
        fields = self.sg.schema_field_read("Version")
        print(fields.keys())


        version_data = {
            "project": {"type": "Project", "id": self.project_id},
            "code": f"{shot_name}_{task_type}_{version_code}",  # <-- 여기 수정!
            "entity": shot_entity,
        }
        version = self.sg.create("Version", version_data)
        if not version:
            print(f" Failed to create Version. Aborting.")
            return
        print(f" Created Version ID: {version.get('id')}")

        # 4) 썸네일 업로드
        if thumbnail_path and thumbnail_path.exists():
            self.sg.upload_thumbnail("Version", version["id"], thumbnail_path.as_posix())
            print(f" Thumbnail uploaded")

        # 5) 영상 업로드 (WebM 우선, 없으면 MP4)
        movie_file = webm_path if webm_path and webm_path.exists() else mp4_path
        if movie_file and movie_file.exists():
            self.sg.upload("Version", version["id"], movie_file.as_posix(), field_name="sg_uploaded_movie")
            print(f" Movie uploaded: {movie_file}")

        print(f"=== Publish End ===\n")


class ShotGridController(QtCore.QObject):
    def __init__(self, ui, project_id: int, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.model = ShotGridModel(project_id)
        self.context = ShotGridContext(project_id)
        self.format_converter = Format_Converter()

        self.ui.load_data_button.clicked.connect(self._on_load_excel)
        self.ui.publish_button.clicked.connect(self._on_publish)

        self.ui.publish_button.setEnabled(False)

    def set_webm_path(self, path: str):
        self.model.set_webm(Path(path))
        self.ui.status_line.setText(f"WebM 경로 설정: {path}")

    def set_mp4_path(self, path: str):
        self.model.set_mp4(Path(path))
        self.ui.status_line.setText(f"MP4 경로 설정: {path}")

    def _msg(self, title: str, text: str) -> None:
        self.ui.status_line.setText(f"[{title}] {text}")

    def _on_load_excel(self):
        excel_file, _ = QtGui.QFileDialog.getOpenFileName(
            self.ui, "Excel 선택", str(Path.home()), "Excel (*.xlsx)"
        )
        if not excel_file:
            return
        try:
            self.model.set_excel(Path(excel_file))
            self.model.load_excel()
            self.context.load_data(self.model)
            self.ui.status_line.setText(f"엑셀 로드 성공: {excel_file}")
            self.ui.publish_button.setEnabled(True)
        except Exception as e:
            self.ui.status_line.setText(f"엑셀 오류: {e}")
            self.ui.publish_button.setEnabled(False)


    def _on_publish(self):
        tbl = self.ui.table
        if tbl.rowCount() == 0:
            self._msg("오류", "테이블에 데이터가 없습니다.")
            return

        raw_path = self.ui.path_edit.text().strip()
        if not raw_path:
            self._msg("오류", "경로가 선택되지 않았습니다.")
            return

        scan_root = Path(raw_path).resolve()
        # 예: /home/rapa/show/scandata_project/product/scan/20250516_2

        # base_root 경로 (product 제거, scandata_project 기준으로 seq 생성)
        if "scandata_project" not in scan_root.parts:
            self._msg("오류", "'scandata_project' 경로를 찾을 수 없습니다.")
            return
        base_idx = scan_root.parts.index("scandata_project")
        base_root = Path(*scan_root.parts[:base_idx + 1]) / "seq"

        try:
            for row in range(tbl.rowCount()):
                check_item = tbl.item(row, SELECT_COL)
                if not check_item or check_item.checkState() != QtCore.Qt.Checked:
                    continue

                shot_name = self._cell(tbl, row, SHOT_NAME_COL)
                seq_folder = self._cell(tbl, row, SEQ).strip()
                shot_folder = self._cell(tbl, row, SHOT).strip()

                # 1. EXR 폴더 재귀 탐색
                exr_search_path = self._find_exr_folder(scan_root, seq_folder, shot_folder)
                if not exr_search_path:
                    print(f" Row {row+1}: EXR 폴더를 찾지 못했습니다.")
                    continue

                print(f" Row {row+1} EXR 검색 경로: {exr_search_path}")
                exr_files = sorted(exr_search_path.glob("*.exr"))
                if not exr_files:
                    print(f" Row {row+1}: EXR 파일 없음 → {exr_search_path}")
                    continue

                version_path_str = self._cell(tbl, row, UNUSED)
                if not version_path_str:
                    print(f" Row {row+1}: UNUSED에 버전 경로가 없습니다.")
                    continue

                version_root = Path(version_path_str)
                version_code = version_root.name

                # 3. 변환 및 복사
                paths = self.format_converter.copy_exr_sequence(
                    exr_files=[str(p) for p in exr_files],
                    destination_root=str(version_root),
                    last_open_dir=str(exr_search_path)
                )
                # 4. ShotGrid 등록
                self.context.publish_version(
                    seq_name=seq_folder,
                    shot_name=shot_name,
                    version_code=version_code,
                    webm_path=Path(paths.get("webm", "")),
                    mp4_path=Path(paths.get("mp4", "")) if paths.get("mp4") else None,
                    thumbnail_path=Path(paths.get("thumb", "")) if paths.get("thumb") else None,
                )

                # 5. UI 업데이트
                self._update_ui_field(tbl, row, MOVIE_PATH_COL, paths.get("webm", ""))
                self._update_ui_field(tbl, row, MP4_PATH_COL, paths.get("mp4", ""))
                self._update_ui_field(tbl, row, THUMB_PATH_COL, paths.get("thumb", ""), is_thumb=True)

            self._msg("완료", "Publish 작업이 완료되었습니다.")

        except Exception as e:
            self._msg("실패", str(e))


    def _find_exr_folder(self, scan_root: Path, seq_name: str, shot_name: str) -> Path | None:
   
        # scan_root 하위에서 .exr 파일이 들어있는 폴더를 재귀적으로 탐색.
        # seq_name 또는 shot_name이 포함된 폴더를 우선 반환.
  
        candidates = []
        for subdir in scan_root.rglob("*"):
            if subdir.is_dir():
                exr_files = list(subdir.glob("*.exr"))
                if exr_files:
                    folder_str = str(subdir).lower()
                    if seq_name.lower() in folder_str or shot_name.lower() in folder_str:
                        return subdir  # 우선 반환
                    candidates.append(subdir)

        return candidates[0] if candidates else None  # fallback

    def _cell(self, table, row: int, col: int) -> str:
        item = table.item(row, col)
        return item.text().strip() if item else ""

    def _update_ui_field(self, table, row: int, col: int, text: str, is_thumb=False):
        if not text:
            return

        if is_thumb:
            pixmap = QtGui.QPixmap(text)
            if not pixmap.isNull():
                label = QtGui.QLabel()
                label.setPixmap(pixmap.scaled(120, 50, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                table.setCellWidget(row, col, label)
                return

        item = table.item(row, col)
        if item:
            item.setText(text)
        else:
            table.setItem(row, col, QtGui.QTableWidgetItem(text))

