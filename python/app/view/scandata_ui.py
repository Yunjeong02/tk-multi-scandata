

from tank.platform.qt import QtCore, QtGui
## resources.qrc -> qt 리소스 정의파일을 수동으로 생성해서 pyrcc5 설치해서 .py 형식으로 변환하여 ui 코드에서 해당 
# 리소스를 사용할 수 있게 등록 (ex:QIcon(":/icons/logo.png") → resources_rc.py를 import 하지 않으면 인식 불가)
from . import resource_rc  # 패키지 모듈 구조에서 상대경로 import 를 통해 내부 파일을 안정적으로 불러오는 방식 
import os 

class Ui_Dialog(object):
    def setupUi(self, Dialog, last_open_dir="/home/rapa/show/"):
        Dialog.setObjectName("Dialog")
        Dialog.resize(700, 500)
        
        # 메인 레이아웃
        main_layout = QtGui.QVBoxLayout(Dialog)
        
        # 경로 입력 & 버튼 레이아웃
        path_layout = QtGui.QHBoxLayout()
        label = QtGui.QLabel("Project Folder:")
        self.path_edit = QtGui.QLineEdit()
        print ("DEBUG : SUCCESS")

        self.path_edit.setFixedWidth(550)
        self.path_edit.setText(last_open_dir)
        self.browse_button = QtGui.QPushButton("Browse Folder")
        self.load_data_button = QtGui.QPushButton("Load")
        
        path_layout.addWidget(label)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_button)
        path_layout.addWidget(self.load_data_button)
        
        main_layout.addLayout(path_layout)
        
        # 테이블 위젯
        self.table = QtGui.QTableWidget()
        self.table.horizontalHeader().setSectionResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.table.setHorizontalScrollBarPolicy(QtGui.Qt.ScrollBarAsNeeded)
        self.table.setSizeAdjustPolicy(QtGui.QAbstractScrollArea.AdjustToContents)
        self.table.setHorizontalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.table.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        
        # 테이블 배경색 설정
        palette = self.table.palette()
        palette.setColor(self.table.backgroundRole(), QtGui.QColor("#1e1e1e"))
        self.table.setPalette(palette)
        
        main_layout.addWidget(self.table)
        
        # 하단 버튼 및 상태 표시 레이아웃
        bottom_layout = QtGui.QHBoxLayout()
        self.excel_save = QtGui.QPushButton("Save")
        self.excel_edit = QtGui.QPushButton("Edit")
        self.publish_button = QtGui.QPushButton("Publish")
  
       # ── Validate 라벨 + 버튼 그룹
        validate_group = QtGui.QVBoxLayout()  # 상단에 라벨 + 아래에 프레임
        
        # (1) 라벨
        validate_label = QtGui.QLabel("Validate")
        validate_label.setAlignment(QtGui.Qt.AlignCenter)
        validate_label.setStyleSheet("font-weight: bold;")  # 굵게 강조
        validate_group.addWidget(validate_label)

        # (2) 프레임 + 2x2 버튼 배치
        validate_wrap = QtGui.QFrame()
        validate_wrap.setFrameShape(QtGui.QFrame.StyledPanel)
        validate_wrap.setFixedHeight(60)  # 높이 조금 더 줌

        grid_layout = QtGui.QGridLayout(validate_wrap)
        grid_layout.setContentsMargins(4, 2, 4, 2)
        grid_layout.setSpacing(4)

        # 버튼 생성
        self.validate_timecode    = QtGui.QPushButton("Time Code")
        self.validate_version     = QtGui.QPushButton("Version")
        self.validate_src_version = QtGui.QPushButton("Source Ver")
        self.validate_editorial   = QtGui.QPushButton("Editorial")

        # 버튼 크기 넉넉히 조절
        for btn in (self.validate_timecode,
                    self.validate_version,
                    self.validate_src_version,
                    self.validate_editorial):
            btn.setFixedSize(90, 26)

        # 버튼 2행 배치
        grid_layout.addWidget(self.validate_timecode,    0, 0)
        grid_layout.addWidget(self.validate_version,     0, 1)
        grid_layout.addWidget(self.validate_src_version, 1, 0)
        grid_layout.addWidget(self.validate_editorial,   1, 1)

        validate_group.addWidget(validate_wrap)

        self.status_line = QtGui.QLineEdit()
        self.status_line.setReadOnly(True)
        self.status_line.setStyleSheet("color: #90ee90;")
        self.status_line.setFixedWidth(200)
        
        bottom_layout.addWidget(self.excel_save)
        bottom_layout.addWidget(self.excel_edit)
        bottom_layout.addWidget(self.publish_button)
        bottom_layout.addWidget(validate_wrap) 
        bottom_layout.addWidget(self.status_line)
        
        main_layout.addLayout(bottom_layout)
        
    def setStyleSheetFromFile(self, widget, style_path):
        if os.path.exists(style_path):
            with open(style_path, 'r') as f:
                widget.setStyleSheet(f.read())
        else:
            print(f"[Warning] style.css not found: {style_path}")
