# model/shotgrid_model.py

from pathlib import Path
import pandas as pd

class ShotGridModel:
    def __init__(self, project_id):
        self.project_id = project_id
        self.df = None
        self.excel_path = None
        self.webm_path = None
        self.mp4_path = None
        self.thumb_path = None

    def set_excel(self, excel_path: Path):
        self.excel_path = excel_path

    def load_excel(self):
        if not self.excel_path or not self.excel_path.exists():
            raise FileNotFoundError(f"엑셀 파일이 없습니다: {self.excel_path}")
        self.df = pd.read_excel(self.excel_path)

    def set_webm(self, webm_path: Path):
        self.webm_path = Path(webm_path)

    def set_mp4(self, mp4_path: Path):
        self.mp4_path = Path(mp4_path)

    def set_thumbnail(self, thumb_path: Path):
        self.thumb_path = Path(thumb_path)

    def iter_rows(self):
        if self.df is None:
            raise ValueError("Excel 데이터가 로드되지 않았습니다.")
        for _, row in self.df.iterrows():
            yield row
