
import os
import re
import ast
from pathlib import Path
from tank.platform.qt import QtCore, QtGui
from ..view.scandata_ui import Ui_Dialog
from ..controller.excel_controller import ExcelController
from ..controller.format_converter import Format_Converter

SELECT, THUMB, SEQ, SHOT, VER, SCAN, FRANGE, TCODE, COLORSPACE, DATETIME, CAM, UNUSED, MOVIE = range(13)

def _decode_timecode(tc_tuple, fps=24):
    if isinstance(tc_tuple, str):
        try:
            tc_tuple = ast.literal_eval(tc_tuple)
        except Exception as e:
            print(f"[WARN] Failed to parse timecode string: {e}, input: {tc_tuple}")
            return ""

    if not isinstance(tc_tuple, (tuple, list)) or len(tc_tuple) < 1:
        print("[WARN] Timecode input is not tuple/list or empty:", tc_tuple)
        return ""

    try:
        total_frames = int(tc_tuple[0])
        hh = total_frames // (3600 * fps)
        mm = (total_frames // (60 * fps)) % 60
        ss = (total_frames // fps) % 60
        ff = total_frames % fps
        return f"{int(hh):02d}:{int(mm):02d}:{int(ss):02d}:{int(ff):02d}"
    except Exception as e:
        print(f"[WARN] Timecode decode failed: {e}, input: {tc_tuple}")
        return ""

class BrowserLoad():
    def __init__(self, ui, dialog=None , excel_ctrl=None, context=None, last_open_dir=None):
        self.ui = ui
        self.dialog = dialog
        self.context = context  # <- 받아두면 추후 Shotgun Context에도 활용 가능
        self.last_open_dir = last_open_dir or "/home/rapa/show/scandata_project/product/scan"

        self.format_converter = Format_Converter()
        self.excel_controller = ExcelController(self.ui.table, self.ui.status_line, self.ui)

        self.ui.excel_save.clicked.connect(self.save_selected_metadata)
        self.ui.table.setColumnCount(13)
        self.ui.table.setHorizontalHeaderLabels([
            "Select", "Thumbnail", "Seq Name", "Shot Name", "Version",
            "Scan Path", "Frame Range", "Timecode", "Colorspace",
            "Date", "Camera", "Unused", "Movie Path"
        ])
        self.ui.browse_button.clicked.connect(self.load_multiple_folders)

    def load_multiple_folders(self):
        base_dir = self.last_open_dir
        dialog = QtGui.QFileDialog(None, "여러 시퀀스 폴더 선택", base_dir)
        dialog.setFileMode(QtGui.QFileDialog.Directory)
        dialog.setOption(QtGui.QFileDialog.DontUseNativeDialog, True)
        dialog.setOption(QtGui.QFileDialog.ShowDirsOnly, True)

        view = dialog.findChild(QtGui.QListView, "listView")
        if view:
            view.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        tree_view = dialog.findChild(QtGui.QTreeView)
        if tree_view:
            tree_view.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        if dialog.exec_():
            selected_folders = dialog.selectedFiles()
            if selected_folders:
                self.last_open_dir = selected_folders[0]               # 최신 선택 경로 저장
                self.ui.path_edit.setText(self.last_open_dir)          # UI 경로 필드에 반영
                print(f"[DEBUG] 사용자가 선택한 경로: {self.last_open_dir}")
                for folder in selected_folders:
                    self._search_and_add_exr_folders(Path(folder))     # 폴더들 탐색 및 테이블에 추가

    def _search_and_add_exr_folders(self, root_folder: Path):
        for dirpath, _, filenames in os.walk(root_folder):
            exr_files = [f for f in filenames if f.endswith(".exr")]
            if exr_files:
                exr_paths = sorted(Path(dirpath) / f for f in exr_files)
                self._add_folder_to_table(Path(dirpath), exr_paths)

    def get_next_version(self, seq_path: Path) -> str:
        version_dirs = [p.name for p in seq_path.iterdir() if p.is_dir() and re.match(r"v\d{3}", p.name)]
        if not version_dirs:
            return "v001"
        
        versions = [int(v[1:]) for v in version_dirs]
        max_version = max(versions)
        next_version = max_version + 1
        return f"v{next_version:03d}"

    def _add_folder_to_table(self, folder_path: Path, exr_files):
        start_frame, end_frame = self._get_frame_range(exr_files)
        timecode, colorspace = self._extract_exr_metadata(exr_files[0])
        timecode = _decode_timecode(timecode)

        shot = folder_path.name
        seq = folder_path.parent.name
        seq_path = folder_path.parent
        print (seq)
        print (shot)

        version = self.get_next_version(seq_path)  # v001 대신 동적으로 최신 버전 계산
        date = self._get_modified_date(folder_path)
        row = self.ui.table.rowCount()
        self.ui.table.insertRow(row)

        check_item = QtGui.QTableWidgetItem()
        check_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        check_item.setCheckState(QtCore.Qt.Checked)
        self.ui.table.setItem(row, SELECT, check_item)

        def set_item(col, text):
            print(f"[DEBUG] set_item col={col}, text={text}")
            item = QtGui.QTableWidgetItem(text if text else "-")
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.ui.table.setItem(row, col, item)

        # 여기서 format_converter 의 generate_thumbnail 호출
        thumb_path_str = self.format_converter.generate_thumbnail(str(exr_files[0]), str(folder_path / ".thumb"))
        if thumb_path_str:
            pixmap = QtGui.QPixmap(thumb_path_str)
            label = QtGui.QLabel()
            label.setPixmap(pixmap.scaled(300, 100, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
            self.ui.table.setRowHeight(row, 110)  # 이미지 높이보다 조금 더 크게
            self.ui.table.setCellWidget(row, THUMB, label)
        else:
            set_item(THUMB, "")  # 없으면 빈칸 처리

        set_item(SEQ, seq)
        set_item(SHOT, shot)
        set_item(VER, version)
        set_item(SCAN, str(folder_path))
        set_item(FRANGE, f"{start_frame}-{end_frame}")
        set_item(TCODE, timecode or "")
        set_item(COLORSPACE, colorspace or "")
        set_item(DATETIME, date)
        set_item(MOVIE, "")

    def save_selected_metadata(self):
        print("[DEBUG] BrowserLoad.save_selected_metadata 호출됨")
        row_count = self.ui.table.rowCount()
        records = []

        for row in range(row_count):
            item = self.ui.table.item(row, SELECT)
            if item and item.checkState() == QtCore.Qt.Checked:
                record = {
                    "SEQ": self.ui.table.item(row, SEQ).text() if self.ui.table.item(row, SEQ) else "",
                    "SHOT": self.ui.table.item(row, SHOT).text() if self.ui.table.item(row, SHOT) else "",
                    "VER": self.ui.table.item(row, VER).text() if self.ui.table.item(row, VER) else "",
                    "SCAN": self.ui.table.item(row, SCAN).text() if self.ui.table.item(row, SCAN) else "",
                    "FRANGE": self.ui.table.item(row, FRANGE).text() if self.ui.table.item(row, FRANGE) else "",
                    "TCODE": self.ui.table.item(row, TCODE).text() if self.ui.table.item(row, TCODE) else "",
                    "COLORSPACE": self.ui.table.item(row, COLORSPACE).text() if self.ui.table.item(row, COLORSPACE) else "",
                    "DATETIME": self.ui.table.item(row, DATETIME).text() if self.ui.table.item(row, DATETIME) else "",
                    "CAM": "",
                    "MOVIE": self.ui.table.item(row, MOVIE).text() if self.ui.table.item(row, MOVIE) else "",
                    "THUMB": "",  # 썸네일은 엑셀 저장 제외하거나 따로 처리하세요
                }
                records.append(record)
                # 체크된 항목이 실제로 있는지 확인용도 
                if item and item.checkState() == QtCore.Qt.Checked:
                    print(f"[DEBUG] 선택된 row: {row}")

        # 디버그 문구 출력 
        if records:
            scan_path = Path(records[0]["SCAN"])
            print(f"선택된 레코드 개수: {len(records)}")
        else:
            self.ui.status_line.setText("선택된 항목이 없습니다.")

        if records: 
            seq_name = records[0]["SEQ"].split("/")[-1]  # 예: "/home/.../20241226_2" → "20241226_2"
            self.excel_controller.save_metadata(records, scan_path, seq_name=seq_name)


    def _get_frame_range(self, files):
        frame_nums = []
        for f in files:
            m = re.search(r"(\d+)(?=\.exr$)", f.name)
            if m:
                frame_nums.append(int(m.group(1)))
        return min(frame_nums), max(frame_nums)


    def _extract_exr_metadata(self, exr_file):
        try:
            meta = self.format_converter._get_exr_header(str(exr_file))
            timecode = meta.get("smpte:TimeCode")
            colorspace = meta.get("oiio:ColorSpace")
            return timecode, colorspace
        except Exception as e:
            print(f"[ERROR] 메타데이터 추출 실패: {e}")
            return None, None

    def _get_modified_date(self, path: Path) -> str:
        return QtCore.QDateTime.fromSecsSinceEpoch(int(path.stat().st_mtime)).toString("yyyy-MM-dd HH:mm:ss")

    def _on_load_excel(self):
        excel_file, _ = QtGui.QFileDialog.getOpenFileName(
            self.dialog,
            "Excel 파일 선택",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        if excel_file:
            # 처리 로직
            pass
