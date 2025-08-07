
from pathlib import Path
from typing import List, Dict, Any
from .excel import ExcelDataModel
from .scan_and_get_frame_range import scan_exr_sequences

class ScanModel:
    def __init__(self):
        # 데이터 저장하는 그릇
        self.data_model = None

    def set_excel_path(self, excel_path):
        self.data_model = ExcelDataModel(excel_path)

    def scan_folder(self, folder_path: str) -> List[Dict[str, Any]]:
        seqs = scan_exr_sequences(folder_path)   # ← [{'basename':..., 'files':[...]} ...]
        self.data_model.clear()
        self.data_model.extend(seqs)
        return seqs                               # **추가: 시퀀스 리스트 반환**

    def get_metadata(self) -> List[Dict[str, Any]]:
        # 저장된 메타데이터 전체 반환
        return self.data_model.all()
