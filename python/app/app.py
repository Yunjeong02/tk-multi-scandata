
from sgtk.platform import Application

class App(Application):
    def init_app(self):
        # app 모듈 import (python/app/__init__.py)
        app_payload = self.import_module("app")

        menu_callback = lambda: app_payload.dialog.show_dialog(self)

        self.engine.register_command("Scan Data Tool", menu_callback)








