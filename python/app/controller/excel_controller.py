import pandas as pd
from pathlib import Path
import re
from tank.platform.qt import QtCore, QtGui
from ..model.excel import ExcelDataModel

class ExcelController(QtGui.QWidget):
    def __init__(self, table_widget, status_line, ui):
        super().__init__()
        self.ui = ui
        self.table = table_widget
        self.status_line = status_line

        self.df = None
        self.excel_path: Path | None = None

        self.ui.excel_save.clicked.connect(self._on_save_clicked)
        self.ui.excel_edit.clicked.connect(self._on_edit_clicked)



    def save_metadata(self, records: list[dict], out_dir: Path, seq_name: str = None):
    
        print("[DEBUG] save_metadata 호출됨")
        versioned_path = self._get_next_excel_version(out_dir, seq_name)
        self.excel_path = versioned_path

        self.df = pd.DataFrame(records)
        print(f"[DEBUG] save_metadata: DataFrame 생성 완료, rows={len(self.df)}")

        # 직접 저장
        self.df.to_excel(self.excel_path, index=False)
        print(f"[DEBUG] save_metadata: 직접 to_excel 호출 완료, 경로: {self.excel_path}")
        self.status_line.setText(f"엑셀 저장: {self.excel_path}")


    ## 사용자가 선택한 seq 이름을 받아서 excel 파일을 생성할 수 있도록 지정 
    def _get_next_excel_version(self, out_dir: Path, seq_name: str | None = None) -> Path:
        base_name = f"metadata_{seq_name}_" if seq_name else "metadata_"
        existing_files = list(out_dir.glob(f"{base_name}v*.xlsx"))
        versions = []
        for f in existing_files:
            m = re.search(rf"{re.escape(base_name)}v(\d{{3}})\.xlsx", f.name)
            if m:
                versions.append(int(m.group(1)))
        next_ver = max(versions) + 1 if versions else 1
        filename = f"{base_name}v{next_ver:03d}.xlsx"
        return out_dir / filename


    def _load_and_show(self, path: Path):
        if not path.exists():
            self.status_line.setText("엑셀 파일이 없습니다.")
            return
        try:
            self.df = pd.read_excel(path)
            print(f"[DEBUG] _load_and_show: 엑셀 로드 완료, row count={len(self.df)}")
            self._df_to_table(self.df)
            self.status_line.setText(f"로드 완료: {path}")
        except Exception as e:
            print(f"[ERROR] _load_and_show: 엑셀 로드 실패: {e}")
            self.df = None
            self.status_line.setText("엑셀 로드 실패")



    def _df_to_table(self, df):
        t = self.table
        t.clear()
        t.setRowCount(len(df))
        t.setColumnCount(len(df.columns))
        t.setHorizontalHeaderLabels(df.columns.tolist())

        for r in range(len(df)):
            for c, col_name in enumerate(df.columns):
                item = QtGui.QTableWidgetItem(str(df.iat[r, c]))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                t.setItem(r, c, item)
        t.resizeColumnsToContents()
        t.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)

    def _on_save_clicked(self):
        print(f"[DEBUG] _on_save_clicked called, current df: {self.df}")
        if self.df is None:
            self.status_line.setText("저장할 데이터가 없습니다 (self.df is None)")
            print("[DEBUG] self.df is None")
            return
        if self.df.empty:
            self.status_line.setText("저장할 데이터가 없습니다 (self.df is empty)")
            print("[DEBUG] self.df is empty")
            return

        out_dir = self.excel_path.parent if self.excel_path else Path.home()
        next_version_path = self._get_next_excel_version(out_dir)

        print(f"[DEBUG] Saving new version to: {next_version_path}")

        self.df = self.df.astype(object)
        for r in range(self.table.rowCount()):
            for c, col in enumerate(self.df.columns):
                item = self.table.item(r, c)
                if item is not None:
                    self.df.iat[r, c] = item.text()

        print(f"[DEBUG] Updated df from table, shape: {self.df.shape}")
        print(f"[DEBUG] df head after update:\n{self.df.head()}")

        self.df.to_excel(next_version_path, index=False)
        self.excel_path = next_version_path
        self.status_line.setText(f"엑셀 새 버전 저장 완료: {self.excel_path}")


    # ---------- slot: Edit 버튼 --------------------------------------

    def _on_edit_clicked(self):
        """테이블 셀 편집 On/Off 토글"""
        editing = self.table.editTriggers() == QtGui.QAbstractItemView.NoEditTriggers
        new_flag = (QtGui.QAbstractItemView.DoubleClicked
                    if editing else QtGui.QAbstractItemView.NoEditTriggers)
        self.table.setEditTriggers(new_flag)

        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if item:
                    if editing:
                        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                    else:
                        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)

        self.ui.excel_edit.setText("Lock" if editing else "Edit")
        self.status_line.setText("편집 모드 ON" if editing else "편집 잠금")


    # # ---------- slot: Browse Folder 버튼 ------------------------------
    # def _on_browse_folder(self):
    #     path, _ = QtGui.QFileDialog.getOpenFileName(
    #         self, "Excel 불러오기", str(Path.home()), "Excel Files (*.xlsx)")
    #     if path:
    #         self.load_metadata(Path(path))
