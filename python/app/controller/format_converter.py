


import re
import os
import sys
import subprocess
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
try:
    from tank.platform.qt import QtCore, QtGui
except ImportError:
    # Qt 임포트 실패시 모의 클래스 정의 (디버깅용)
    class QtGui:
        class QWidget:
            def __init__(self): pass

# ---------------------------------------------------------------------
# 0. Rez 경로 세팅 & OIIO 로더
# ---------------------------------------------------------------------
REZ_ROOT = "/home/rapa/rez/rez_install"
REZ_SITEPKG = os.path.join(REZ_ROOT, "lib/python3.9/site-packages")
REZ_ENV_CMD = "/home/rapa/rez/rez_install/bin/rez/rez-env"
REZ_OIIO_PKG = "oiio-2.5.13"


def _ensure_oiio():
    try:
        import OpenImageIO as oiio
        return oiio
    except ImportError:
        pass

    # 1) site‑packages 경로 추가
    if os.path.isdir(REZ_SITEPKG) and REZ_SITEPKG not in sys.path:
        sys.path.append(REZ_SITEPKG)
        try:
            import OpenImageIO as oiio
            return oiio
        except ImportError:
            pass

    # 2) LD_LIBRARY_PATH 패치 후 재시도
    rez_lib = Path(REZ_ROOT) / "packages/oiio/2.5.13/platform-linux/arch-x86_64/lib"
    os.environ["LD_LIBRARY_PATH"] = f"{rez_lib}:{os.environ.get('LD_LIBRARY_PATH','')}"
    try:
        import OpenImageIO as oiio
        return oiio
    except ImportError:
        print("[ERROR] OIIO import still failing; falling back to rez‑env calls")
        return None            # ← None 이면 _get_exr_header_via_rez 사용

_OIIO = _ensure_oiio()


class Format_Converter(QtGui.QWidget):

    def __init__(self):
        super().__init__()

    #### 이 부분 코드 공부해보기. subprocess 로 rez-env 환경을 실행시켜서 oiio 툴을 실행시켜 이미지를 
    ## 코드 내에서 읽을 수 있도록 하는 코드인데, 조금 더 공부가 필요할 것 같음. 
    def _read_exr_direct(self, exr_path):
        img = _OIIO.ImageInput.open(str(exr_path))
        if not img:
            raise RuntimeError(f"OpenImageIO failed to open: {exr_path}")
        spec = img.spec()
        pixels = img.read_image(format=_OIIO.FLOAT)
        img.close()
        return spec.width, spec.height, spec.nchannels, pixels

    def _read_exr_via_rez(self, exr_path):
        tmp_npy = Path(exr_path).with_suffix(".npy")
        py_code = (
            "import numpy as np, OpenImageIO as oiiotool, sys, pathlib;"
            "p=sys.argv[1];"
            "img=oiiotool.ImageInput.open(p);"
            "spec=img.spec();"
            "px=np.array(img.read_image(format=oiiotool.FLOAT));"
            "img.close();"
            "np.save(pathlib.Path(p).with_suffix('.npy'), px);"
            "print(f'{spec.width},{spec.height},{spec.nchannels}')"
        )
        cmd = [REZ_ENV_CMD, REZ_OIIO_PKG, "--", "python", "-c", py_code, str(exr_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr)
        w, h, c = map(int, proc.stdout.strip().split(","))
        pixels = np.load(tmp_npy)
        tmp_npy.unlink(missing_ok=True)
        return w, h, c, pixels

    def _read_exr(self, exr_path):
        import OpenImageIO as oiio
        img = oiio.ImageInput.open(exr_path)
        if not img:
            raise Exception(f"파일을 열 수 없음: {exr_path}")
        spec = img.spec()
        w, h, nch = spec.width, spec.height, spec.nchannels
        pixels = img.read_image()
        img.close()
        if pixels is None:
            raise Exception(f"픽셀 데이터가 없음: {exr_path}")
        return w, h, nch, pixels

    # return json.loads(proc.stdout)
    def _get_exr_header_via_rez(self, exr_path: str) -> dict:
        py_code = (
            "import json, OpenImageIO as oiio, sys\n"
            "img = oiio.ImageInput.open(sys.argv[1])\n"
            "if not img:\n"
            "    raise RuntimeError('Cannot open ' + sys.argv[1])\n"
            "spec = img.spec()\n"
            "metadata = {}\n"
            "try:\n"
            "    names = spec.extra_attrib_names()\n"
            "    for k in names:\n"
            "        v = spec.extra_attrib(k)\n"
            "        metadata[k] = str(v)\n"
            "except AttributeError:\n"
            "    try:\n"
            "        for attr in spec.extra_attribs:\n"
            "            metadata[str(attr.name)] = str(attr.value)\n"
            "    except Exception:\n"
            "        pass\n"
            "img.close()\n"
            "print(json.dumps(metadata))\n"
        )
        cmd = [
            REZ_ENV_CMD, REZ_OIIO_PKG, "--",
            "python", "-c", py_code, exr_path
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        if proc.returncode != 0:
            raise RuntimeError(proc.stderr)

        # JSON 문자열 → dict 변환
        import json
        meta = json.loads(proc.stdout)

        # 디버깅 출력
        print("\n[✅ EXR Metadata Keys]")
        for k in sorted(meta.keys()):
            print("-", k)

        print("\n[DEBUG 주요 KEY 추출]")
        for key in ["smpte:TimeCode", "cameraModel", "oiio:ColorSpace"]:
            print(f"{key}: {meta.get(key)}")
        return meta

    def _get_exr_header(self, exr_path: str) -> dict:
        try:
            import OpenImageIO as oiio
        except ImportError:
            # <─ oiio import 실패 → Rez 우회
            return self._get_exr_header_via_rez(exr_path)

        img = oiio.ImageInput.open(exr_path)
        if not img:
            raise RuntimeError(f"Cannot open EXR: {exr_path}")
        spec = img.spec()
        meta = {k: spec.extra_attrib(k) for k in spec.extra_attrib_names()}
        img.close()
        return meta
    # ───────────────────────────────────────────────────────────────
    # frame number 설정 
    @staticmethod
    def _replace_numeric_suffix(name: str, num: int, width: int = 4) -> str:
        """
        'shot_A_0032'  →  'shot_A_1001'
        숫자가 없으면   foo.exr      →  foo_1001.jpg
        """
        import re
        m = re.search(r"(.*?)(\d+)(\D*)$", name)   # 끝의 숫자 패턴
        if m:
            prefix, _, postfix = m.groups()
            return f"{prefix}{num:0{width}d}{postfix}"
        else:
            return f"{name}_{num:0{width}d}"
    # ------------------------------------------------------------
    #  EXR → JPG
    # ------------------------------------------------------------
    def convert_all_exr_to_jpg(
        self,
        exr_files: list[str],
        output_dir: str,
        clone_to: str | None = None
    ) -> None:
        print(f"[INFO] EXR 파일 개수: {len(exr_files)}")

        # EXR 복제 (옵션)
        if clone_to:
            clone_dir = Path(clone_to)
            clone_dir.mkdir(parents=True, exist_ok=True)
            for src in exr_files:
                shutil.copy2(src, clone_dir / Path(src).name)
            print(f"[INFO] EXR 복제 완료 → {clone_dir}")
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        start_num = 1001
        for idx, exr_path in enumerate(exr_files):
            stem     = Path(exr_path).stem
            new_stem = self._replace_numeric_suffix(stem, start_num + idx)  # ← self.
            jpg_path = out_dir / f"{new_stem}.jpg"
            if jpg_path.exists():
                print(f"[SKIP] {jpg_path.name} 이미 존재"); continue

            print(f"[{start_num + idx}] 변환 중: {exr_path}")
            try:
                w, h, nch, pix = self._read_exr_via_rez(exr_path)
            except Exception as e:
                print(f"[ERROR] {exr_path} 읽기 실패: {e}"); continue

            rgb = np.array(pix).reshape(h, w, nch)
            rgb = rgb[:, :, :3] if nch >= 3 else np.repeat(rgb[:, :, 0:1], 3, axis=2)
            rgb = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
            Image.fromarray(rgb, mode="RGB").save(jpg_path, "JPEG")
            print(f"[INFO] 저장 완료: {jpg_path}")

    ### 썸네일 추출 코드 
    def generate_thumbnail(self, exr_path: str, output_dir: str) -> str:
        thumb_dir = Path(output_dir)
        thumb_dir.mkdir(parents=True, exist_ok=True)

        # 썸네일이 이미 존재한다면 생성과정 생략
        if (thumb_dir / "thumb_1080.jpg").exists():
            print("[INFO] 썸네일 이미 존재 – 생성 생략")
            return str(thumb_dir / "thumb_1080.jpg")
        if (thumb_dir / "thumb_1k.jpg").exists():
            print("[INFO] 썸네일 이미 존재 – 생성 생략")
            return str(thumb_dir / "thumb_1k.jpg")
        try:
            w, h, nch, pix = self._read_exr_via_rez(exr_path)
        except Exception as e:
            print(f"[ERROR] 썸네일 생성 실패: {e}")
            return ""

        rgb = np.array(pix).reshape(h, w, nch)
        rgb = rgb[:, :, :3] if nch >= 3 else np.repeat(rgb[:, :, 0:1], 3, axis=2)
        rgb = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
        pil_img = Image.fromarray(rgb, mode="RGB")

        # 이미지 사이즈 1080 , 2040 으로 두 버전으로 추출
        if w >= 3840 and h >= 2160:  # 4K 이상
            pil_img.resize((1920, 1080), Image.LANCZOS).save(thumb_dir / "thumb_1080.jpg")
            pil_img.resize((2048, 1080), Image.LANCZOS).save(thumb_dir / "thumb_2k.jpg")
            return str(thumb_dir / "thumb_1080.jpg")
        else:  # 4K 미만
            ratio = 1080 / max(w, h)
            new_size = (round(w * ratio), round(h * ratio))
            pil_img.resize(new_size, Image.LANCZOS).save(thumb_dir / "thumb_1k.jpg")
            pil_img.save(thumb_dir / "thumb_full.jpg")
            return str(thumb_dir / "thumb_1k.jpg")

    def generate_webm_video(self, jpg_output_dir, mp4_output_dir):
        jpg_dir      = Path(jpg_output_dir).resolve()
        jpg_files    = sorted(jpg_dir.glob("*.jpg"))
        if not jpg_files:
            print("[ERROR] JPG 파일 없음 – 영상 생성 중단"); return

        # ── ① 첫 JPG 이름에서 숫자 패턴 찾아 FFmpeg 입력 패턴 생성 ──
        sample = jpg_files[0].name                    # ex) shot_A_1001.jpg
        m = re.search(r"(.*?)(\d+)(\.jpg)$", sample)
        if not m:
            print(f"[ERROR] 패턴 추출 실패: {sample}"); return
        prefix, num_str, suffix = m.groups()
        input_pattern = str(jpg_dir / f"{prefix}%0{len(num_str)}d{suffix}")
        start_number  = int(num_str)
        # ── ② 기존 경로·환경 설정 동일 ──
        webm_path = jpg_dir.parent / "webm" / "output_video.webm"
        mp4_path  = Path(mp4_output_dir).resolve() / "output_video.mp4"
        webm_path.parent.mkdir(parents=True, exist_ok=True)
        mp4_path.parent.mkdir(parents=True,  exist_ok=True)

        ffmpeg       = "/home/rapa/local_packages/ffmpeg/7.1.1/platform-linux/arch-x86_64/bin/ffmpeg"
        libvpx_lib   = "/home/rapa/local_packages/libvpx/1.14.0/lib"
        env          = os.environ.copy()
        env["LD_LIBRARY_PATH"] = f"{libvpx_lib}:{env.get('LD_LIBRARY_PATH', '')}"

        # ── ③ WebM ──
        cmd_webm = [
            ffmpeg, "-framerate", "24",
            "-start_number", str(start_number),   
            "-i", input_pattern,
            "-pix_fmt", "yuv420p", "-c:v", "libvpx", "-b:v", "1M",
            "-c:a", "libvorbis", "-y", str(webm_path)
        ]
        res = subprocess.run(cmd_webm, capture_output=True, text=True, env=env)
        print(f"[INFO] WebM 비디오 생성 완료: {webm_path}" if res.returncode==0 else res.stderr)

        # ── ④ MP4 ──
        cmd_mp4 = [
            ffmpeg, "-framerate", "24",
            "-start_number", str(start_number),
            "-i", input_pattern,
            "-pix_fmt", "yuv420p", "-c:v", "mpeg4", "-qscale:v", "2",
            "-y", str(mp4_path)
        ]
        res2 = subprocess.run(cmd_mp4, capture_output=True, text=True, env=env)
        print(f"[INFO] MP4 비디오 생성 완료: {mp4_path}" if res2.returncode==0 else res2.stderr)
        return {"webm": str(webm_path), "mp4": str(mp4_path)}
    
    # ────────────────────────────────────────────────
    #  ffmpeg로 EXR 시퀀스를 MOV로 변환할 때, 감마 2.2를 적용
    # ────────────────────────────────────────────────
    def convert_exr_sequence_to_mov(
        self,
        exr_sequence_dir: str,
        mov_output_path: str,
        start_number: int = 1001,
        framerate: int = 24
    ) -> str:
        """
        EXR 시퀀스를 MOV (ProRes) 로 변환하며 감마 2.2 적용
        """
        from pathlib import Path
        import os, subprocess, re

        exr_dir = Path(exr_sequence_dir)
        mov_path = Path(mov_output_path)
        mov_path.parent.mkdir(parents=True, exist_ok=True)

        files = sorted(exr_dir.glob("*.exr"))
        if not files:
            raise RuntimeError(f"EXR 파일이 없습니다: {exr_sequence_dir}")

        sample_name = files[0].name
        m = re.search(r"(.*?)(\d+)(\.exr)$", sample_name)
        if not m:
            raise RuntimeError(f"EXR 파일 이름에 번호 패턴이 없습니다: {sample_name}")

        prefix, num_str, suffix = m.groups()
        input_pattern = str(exr_dir / f"{prefix}%0{len(num_str)}d{suffix}")

        ffmpeg_bin = "/home/rapa/local_packages/ffmpeg/7.1.1/platform-linux/arch-x86_64/bin/ffmpeg"
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = "/home/rapa/local_packages/libvpx_backup/lib:" + env.get("LD_LIBRARY_PATH", "")

        # 감마 2.2 적용 + ProRes
        cmd = [
        ffmpeg_bin,
        "-framerate", str(framerate),
        "-start_number", str(start_number),
        "-i", input_pattern,
        # "-vf", "lut=r=pow(val\\,1/2.2):g=pow(val\\,1/2.2):b=pow(val\\,1/2.2)",  # ← 쉼표는 백슬래시로 escape
        "-c:v", "prores_ks",
        "-profile:v", "3",                   # HQ
        "-pix_fmt", "yuv422p10le",
        "-y",
        str(mov_path)
    ]
        print(f"[INFO] MOV 변환 실행: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if res.returncode != 0:
            print(f"[ERROR] MOV 변환 실패: {res.stderr}")
            raise RuntimeError("MOV 변환 실패")

        print(f"[INFO] MOV 변환 완료: {mov_path}")
        return str(mov_path)
   
    # ────────────────────────────────────────────────
    #  핵심: 경로 dict 를 리턴하도록 수정
    # ────────────────────────────────────────────────
    
    def copy_exr_sequence(
        self,
        exr_files: list[str],
        destination_root: str,
        last_open_dir: str | None = None,
    ) -> dict[str, str]:               # ← 반환형 변경
        """
        EXR 시퀀스를 JPG·WebM·MP4 로 변환한 뒤
        {'thumb': str, 'webm': str, 'mp4': str} 를 반환한다.
        """
        # ── 0) base dir 보정 ─────────────────────────
        if last_open_dir is None:
            if not exr_files:
                raise ValueError("exr_files 가 비어있습니다.")
            last_open_dir = os.path.dirname(exr_files[0])

        exr_files = [os.path.realpath(p if os.path.isabs(p)
                                      else os.path.join(last_open_dir, p))
                     for p in exr_files]

        # ── 1) 출력 폴더 ─────────────────────────────
        jpg_dir = Path(destination_root) / "jpg"
        mp4_dir = Path(destination_root) / "mp4"
        mov_dir = Path(destination_root) / "mov"      # MOV 저장 폴더 추가
        org_dir = Path(destination_root) / "org"

        jpg_dir.mkdir(parents=True, exist_ok=True)
        mp4_dir.mkdir(parents=True, exist_ok=True)
        mov_dir.mkdir(parents=True, exist_ok=True)
        org_dir.mkdir(parents=True, exist_ok=True)

        # ── 2) EXR → JPG ────────────────────────────
        self.convert_all_exr_to_jpg(exr_files, str(jpg_dir))
        if not list(jpg_dir.glob("*.jpg")):
            raise RuntimeError("JPG 변환 실패 – oiio/권한 확인")

        # ── 3) 썸네일 생성 ──────────────────────────
        self.generate_thumbnail(exr_files[0], str(jpg_dir))
        thumb_path = jpg_dir / "thumb_1080.jpg"
        if not thumb_path.exists():                      # 4K 미만이면 1K 썸네일
            thumb_path = jpg_dir / "thumb_1k.jpg"

        # ── 4) 영상 생성 ─────────────────────────────
        vid_paths = self.generate_webm_video(str(jpg_dir), str(mp4_dir))

        # ──  exr 복제  ─────────────────────────────
        # 샷 이름 추출: 파일 이름에서 prefix 추출 (ex: "S008SH0040")
        original_name = Path(exr_files[0]).name
        m = re.match(r"(.+?)[._-]?\d+\.(exr)$", original_name)
        if not m:
            raise RuntimeError(f" 파일 이름에서 샷 코드 추출 실패: {original_name}")
        shot_name = m.group(1)

        renamed_exr_files = []
        for i, path in enumerate(sorted(exr_files), start=1001):
            new_name = f"{shot_name}_{i:04d}.exr"
            dst = org_dir / new_name
            shutil.copy2(path, dst)
            renamed_exr_files.append(str(dst))

        # ── 5) MOV 생성 ─────────────────────────────
        mov_output_path = mov_dir / "output_video.mov"
        mov_path_str = self.convert_exr_sequence_to_mov(
            exr_sequence_dir=str(org_dir),  # ★ 복제된 org 폴더에서
            mov_output_path=str(mov_output_path),
            start_number=1001,
            framerate=24,
        )
        
        # ── 6) 호출자에게 경로 반환 ──────────────────
        return {
            "thumb": str(thumb_path),
            "webm" : vid_paths["webm"],
            "mp4"  : vid_paths["mp4"],
            "mov": mov_path_str,
        }

