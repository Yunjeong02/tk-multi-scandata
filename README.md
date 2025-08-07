

# IO Manager Tool  
**SGTK 기반 EXR 시퀀스 메타데이터 관리 & 퍼블리싱 툴**

이 툴은 ShotGrid Toolkit(SGTK)을 기반으로 구축된 GUI 툴로,  
EXR 이미지 시퀀스를 탐색, 편집, 유효성 검증 및 퍼블리싱하는 전체 워크플로우를 지원합니다.  
OpenImageIO(OIIO)를 Rez 환경 내 subprocess로 실행해 메타데이터 추출 안정성을 확보했으며,  
Excel 기반 저장 및 ShotGrid 퍼블리싱까지 손쉽게 처리할 수 있도록 설계되었습니다.


- Browse: EXR 시퀀스 탐색 및 정렬
- 메타데이터 추출: OIIO subprocess 실행
- UI 테이블 표시: PySide 기반 시각화 + 체크박스 선택
- Edit: 테이블 편집 모드 전환
- Save: Excel(.xlsx)로 버전 저장
- Validate: 퍼블리싱 유효성 검사 (timecode, 경로, 버전 등)
- Publish: JPG/MP4/WEBM/MOV 변환 + ShotGrid 퍼블리싱 연동


## 아키텍처 구조 (Custom MVC 구조)

본 프로젝트는 기능 단위로 모듈화된 **실용적 MVC 구조**를 기반으로 구성되어 있습니다.  
각 모듈은 Model, View, Controller로 명확히 분리되어 있으며,  
모든 모듈은 `dialog.py`를 중심으로 연결되고 실행됩니다.

---
### View

- **scandata_ui.py**  
  PySide2 기반 UI 정의 파일로, 전체 GUI의 시각적 구성과 위젯 배치를 담당합니다.  
  사용자 입력을 수신하고, 화면 요소를 렌더링하는 **View**로서의 역할을 수행합니다.

---
### Model

- **browse_data.py**  
  탐색된 EXR 시퀀스 데이터를 리스트/딕셔너리 형태로 정리하여 제공합니다.

- **excel.py**  
  UI 테이블 데이터를 pandas DataFrame으로 관리하며, Excel 저장/불러오기에 필요한 데이터 모델을 구성합니다.

- **scan_and_get_frame_range.py**  
  EXR 파일의 시퀀스를 스캔하고, 프레임 범위를 계산하여 시퀀스 단위로 묶어주는 로직을 담고 있습니다.

- **shotgrid_model.py**  
  ShotGrid 퍼블리싱을 위한 메타데이터 구조 및 필드 매핑 정보를 정의합니다.

- **validate_model.py**  
  퍼블리싱 유효성 검사를 위한 기준 정보(timecode, 경로, 버전 등)를 보관합니다.

> Model 모듈들은 **로직 실행보다는 데이터 정의 및 전달**에 중점을 둡니다.

---
### Controller

- **browse_load.py**  
  사용자가 선택한 폴더에서 EXR 시퀀스를 탐색하고, 시퀀스를 구분해 UI로 전달합니다.

- **excel_controller.py**  
  pandas 기반 DataFrame을 Excel 파일로 버전 넘버링 저장하거나, 기존 Excel 파일을 불러와 테이블에 주입하는 기능을 담당합니다.

- **format_converter.py**  
  EXR 시퀀스를 JPG, MP4, WEBM, MOV 등의 포맷으로 변환합니다. (FFmpeg 또는 외부 툴 사용)

- **shotgrid_controller.py**  
  ShotGrid 퍼블리싱 API와 연결되어, 메타데이터를 업로드하고 각 포맷의 파일을 등록합니다.

- **validate_controller.py**  
  퍼블리싱 전 필수 체크 항목(타임코드, 경로, 필드값 등)을 검증하고, 실패 시 경고창을 출력합니다.

> Controller 모듈은 **사용자 인터랙션에 따라 기능을 실행하는 실제 동작 유닛**입니다.

---
### dialog.py: 모든 흐름의 중심

`dialog.py`는 전체 UI를 구성하고 위 컨트롤러 및 모델 모듈을 호출하는 **애플리케이션의 중심 허브**입니다.

- 모든 버튼 클릭 이벤트는 dialog.py에서 발생
- 모델에서 데이터를 받아오고, 컨트롤러를 통해 로직 실행 후
- 다시 View(UI 테이블)에 반영하는 구조로 구성되어 있습니다

> 실질적인 `main.py` 역할을 수행하며, 전체 앱의 **진입점이자 조율자**입니다.

---
### 디렉터리 구조 
tk-multi-scandata/
├── app.py                        ← Rez subprocess 테스트용 (standalone)
├── __init__.py                   ← 루트 패키지 초기화 (필요시 비워둠)
├── icon_256.png                  ← 앱 아이콘 리소스
├── python/
│   ├── __init__.py               ← SGTK에서 앱 모듈 로딩 시 진입점
│   └── app/
│       ├── __init__.py           ← from . import dialog (SGTK 규칙)
│       ├── app.py                ← SGTK Application 클래스(init_app), 메뉴 등록
│       ├── dialog.py             ← 앱 진입점이자 View-Model-Controller 연결 허브
│       ├── view/
│       │   └── scandata_ui.py    ← UI 정의 파일 (View)
│       ├── model/
│       │   ├── browse_data.py
│       │   ├── excel.py
│       │   ├── scan_and_get_frame_range.py
│       │   ├── shotgrid_model.py
│       │   └── validate_model.py
│       └── controller/
│           ├── browse_load.py
│           ├── excel_controller.py
│           ├── format_converter.py
│           ├── shotgrid_controller.py
│           └── validate_controller.py


<!-- 본 프로젝트는 기능 분리와 유지보수를 고려한 디렉터리 구조로 구성되어 있습니다.

- `app.py` : Rez 환경에서 OIIO subprocess 테스트용 standalone 실행 스크립트입니다.
- `python/app/app.py` : SGTK Application 클래스가 정의된 진입점 파일로, 앱 초기화 및 메뉴 등록을 담당합니다.
- `python/app/dialog.py` : View-Model-Controller를 연결하는 **중앙 허브**로, 사용자의 모든 액션이 이곳을 통해 조율됩니다.
- `python/app/view/` : PySide2 기반 UI 구성 요소를 정의합니다.
- `python/app/model/` : 데이터 구조 및 시퀀스 정보, 퍼블리싱 조건 등을 보관합니다.
- `python/app/controller/` : 사용자 액션에 따른 기능 실행 로직을 분리한 컨트롤러 모듈입니다. -->
