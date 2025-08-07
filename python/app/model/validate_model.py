# validation_model.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

@dataclass
class ValidationData:
    # 입력 값
    filepath: Path            # 결과물 mov / exr 첫 프레임 등
    start_frame: int
    end_frame: int
    fps: float
    version_int: int          # 3 → v003
    src_version: str          # "v003"
    shot_name: str
    editorial_list: List[str] = field(default_factory=list)

@dataclass
class ValidationResult:
    name: str                 # 'Timecode', …
    passed: bool = True
    errors: List[str] = field(default_factory=list)

    def add(self, msg: str):
        self.passed = False
        self.errors.append(msg)
