
import re, os
from pathlib import Path

def extract_frame_range_from_sequence(file_list):  # exr 리스트만 반환 
    frame_numbers = []
    for file_path in file_list:
        basename = os.path.basename(file_path)
        match = re.search(r'(\d{4})\.(exr|dpx)$', basename)
        if not match:
            match = re.search(r'_(\d{4})\.', basename)
        if match:
            frame_numbers.append(int(match.group(1)))
    if not frame_numbers:
        return "Unknown"
    return f"{min(frame_numbers):04d} ~ {max(frame_numbers):04d}"

def scan_exr_sequences(folder_path): # 프레임 범위만 추출 

    exr_files = list(Path(folder_path).rglob("*.exr"))
    sequences = {}
    pattern = re.compile(r"(.*)_(\d+)$")  # 파일명 끝 숫자 시퀀스 분리용
    
    for f in exr_files:
        stem = f.stem  # ex: '20241226_2_0001'
        m = pattern.match(stem)
        if m:
            base_name = m.group(1)  # ex: '20241226_2'
            sequences.setdefault(base_name, []).append(str(f))
        else:
            sequences.setdefault(stem, []).append(str(f))
    
    result = []
    for base, files in sequences.items():
        files.sort()
        result.append({"basename": base, "files": files})
    
    return result
