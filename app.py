
# -*- coding: utf-8 -*-
"""
app.py (SGTK Application Entry Point)

- rez‑env 로 별도 서브프로세스에서 OIIO 실행
- stdout/stderr 를 그대로 SGTK logger 로 전달
- 단독 실행 시에도 동작 확인 가능
"""
import os
import sys
import subprocess
from sgtk.platform import Application

# -------------------------------------------------
# 1. rez 설치 경로 & rez‑env 절대경로 지정
# -------------------------------------------------
REZ_ROOT = "/home/rapa/rez/rez_install"
REZ_SITEPKG = os.path.join(REZ_ROOT, "lib/python3.9/site-packages")
REZ_ENV_CMD = os.path.join(REZ_ROOT, "bin/rez/rez-env")      # <-- 중요!

if os.path.isdir(REZ_SITEPKG) and REZ_SITEPKG not in sys.path:
    sys.path.append(REZ_SITEPKG)

# (필요 시 rez API 사용)
try:
    from rez.resolved_context import ResolvedContext
except ImportError:
    ResolvedContext = None

# -------------------------------------------------
# 2. OIIO import 테스트 (직접 import 방식)
# -------------------------------------------------
def test_local_oiio_import():
    """현재 파이썬 프로세스에서 OIIO가 import 되는지 확인"""
    try:
        import OpenImageIO as oiio
        return f"OK – version {oiio.VERSION_STRING}"
    except Exception as e:
        return f"FAILED – {e}"

# -------------------------------------------------
# 3. rez‑subprocess 로 OIIO 정보 가져오기
# -------------------------------------------------
def run_oiio_info_via_rez(image_path, rez_pkg="oiio-2.5.13"):
    """
    rez-env <pkg> -- python -c "<oiio 코드>" 를 실행하고
    결과(stdout/err) 를 문자열로 리턴
    """
    # 경로 escape (큰따옴표 안에 넣을 수 있게)
    esc_path = image_path.replace("\\", "\\\\").replace('"', '\\"')

    py_snippet = (
        "from OpenImageIO import ImageBuf;"
        f"img=ImageBuf(\"{esc_path}\");"
        "spec=img.spec();"
        "print(f'{spec.width}x{spec.height} | {spec.nchannels}ch')"
    )

    cmd = [REZ_ENV_CMD, rez_pkg, "--", "python", "-c", py_snippet]

    proc = subprocess.run(cmd, capture_output=True, text=True)

    return proc.stdout.strip(), proc.stderr.strip(), proc.returncode

# -------------------------------------------------
# 4. SGTK App 클래스
# -------------------------------------------------
class App(Application):
    def init_app(self):
        os.environ.setdefault("REZ_PACKAGES_PATH", "/home/rapa/local_packages")
        self.logger.info("=== Scan Data Tool initializing ===")

        # 4‑1. local import test
        self.logger.info(f"Local OIIO import check → {test_local_oiio_import()}")

        # 4‑2. rez‑subprocess test (경로 반드시 존재!)
        test_img = "/home/rapa/test.jpg"
        if os.path.isfile(test_img):
            out, err, rc = run_oiio_info_via_rez(test_img)
            self.logger.info("--- rez‑subprocess result ---")
            self.logger.info(f"CMD return code : {rc}")
            if out:
                self.logger.info(f"STDOUT : {out}")
            if err:
                self.logger.error(f"STDERR : {err}")
            self.logger.info("------------------------------")
        else:
            self.logger.warning(f"Test image NOT found: {test_img}")

        # 4‑3. SGTK 메뉴 등록
        app_payload = self.import_module("app")   # python/app/__init__.py
        self.engine.register_command(
            "Scan Data Tool",
            lambda: app_payload.dialog.show_dialog(self)
        )
