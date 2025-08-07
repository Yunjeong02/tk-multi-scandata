

from pathlib import Path
import pandas as pd

class ExcelDataModel:
    def __init__(self, excel_path: str | Path):
        self.excel_path = Path(excel_path)

    def save(self, records: list[dict]) -> None:
        """
        메타데이터 records 를 엑셀로 저장합니다.
        """
        df = pd.DataFrame(records)
        self.excel_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(self.excel_path, index=False)

    def load(self) -> pd.DataFrame:
        """
        저장된 엑셀을 DataFrame 형태로 불러옵니다.
        """
        if not self.excel_path.exists():
            raise FileNotFoundError(f"[ERROR] Excel 파일이 존재하지 않습니다: {self.excel_path}")
        return pd.read_excel(self.excel_path)

    def exists(self) -> bool:
        """
        파일 존재 여부 확인
        """
        return self.excel_path.exists()
