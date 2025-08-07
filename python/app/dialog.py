
import sgtk
from tank.platform.qt import QtCore, QtGui
from .view.scandata_ui import Ui_Dialog
from .controller.browse_load import BrowserLoad
from .controller.excel_controller import ExcelController
from .controller.validate_controller import ValidationController
from .controller.shotgrid_controller import ShotGridController

logger = sgtk.platform.get_logger(__name__)

def show_dialog(app_instance):
    app_instance.engine.show_dialog("Scan Data Tool", app_instance, AppDialog)

class AppDialog(QtGui.QWidget):
    def __init__(self, parent=None):
        super(AppDialog, self).__init__(parent)
        logger.info("Starting IO Manager.....")

        # UI 연결
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # 컨텍스트 세팅
        self._app = sgtk.platform.current_bundle()
        self.context = self._app.context
        self.last_open_dir = "/home/rapa/show/scandata_project"

        # 컨트롤러 초기화
        self._init_controllers()

    def _init_controllers(self):
        # ExcelController 먼저 생성
        self.excel_controller = ExcelController(
            table_widget=self.ui.table,
            status_line=self.ui.status_line,
            ui=self.ui
        )

        # BrowserLoad 에 넘겨주기
        self.browser_controller = BrowserLoad(
            ui=self.ui,
            dialog = self,
            context=self.context,
            last_open_dir=self.last_open_dir,
            excel_ctrl=self.excel_controller
        )

        self.validate_controller = ValidationController(self.ui)

        # 신규 ShotGridController 추가
        project_id = self.context.project["id"] if self.context and self.context.project else None
        if project_id is None:
            logger.warning("Context project ID가 없습니다. ShotGridController 생성 불가.")
        else:
            self.shotgrid_controller = ShotGridController(
                ui=self.ui,
                project_id=project_id
            )
