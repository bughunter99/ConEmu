# ConEmu Python 변환 5단계 계획

> ConEmu 터미널 에뮬레이터를 Python으로 변환하기 위한 단계별 실행 계획입니다.

---

## 전략 개요

ConEmu는 약 18만 줄 이상의 C++ 코드로 이루어진 복잡한 Windows 전용 애플리케이션입니다.  
완전한 기능 복제보다는 **핵심 기능(터미널 에뮬레이션 + GUI)** 을 Python으로 구현하는 것을 목표로 합니다.  
변환은 **테스트 가능한 단위**로 나눠 단계별로 진행합니다.

---

## 1단계: 환경 설정 및 프로토타입 (Foundation)

**목표:** Python 프로젝트 뼈대를 만들고 기본 창과 터미널 프로세스 실행을 확인합니다.

### 작업 항목
- [ ] `pyversion/` 폴더 내 Python 프로젝트 구조 초기화
  ```
  pyversion/
    ├── main.py          ← 진입점
    ├── app.py           ← 애플리케이션 클래스 (CConEmuMain 대응)
    ├── terminal/        ← 터미널 에뮬레이션 모듈
    ├── gui/             ← GUI 위젯 모듈
    ├── ipc/             ← 프로세스 통신 모듈
    ├── config/          ← 설정 관리 모듈
    ├── tests/           ← 단위 테스트
    └── requirements.txt
  ```
- [ ] 의존 라이브러리 설치 및 검증 (`PyQt6`, `pyte`, `psutil`, `pywinpty`)
- [ ] PyQt6로 기본 빈 창 생성 (`QMainWindow`)
- [ ] `subprocess.Popen` + `pywinpty` (Windows) 또는 `ptyprocess` (Linux/Mac)로 `cmd.exe` / `bash` 실행
- [ ] 기본 입출력 연결 확인 (읽기/쓰기 스트림)

### 성공 기준
- Python 창이 뜨고 백그라운드에서 쉘 프로세스가 실행됨
- 쉘 프로세스에 `echo hello` 전송 시 `hello` 출력을 받을 수 있음

---

## 2단계: 터미널 에뮬레이터 코어 구현 (Terminal Engine)

**목표:** `CRealConsole` + `ConEmuCD` 역할을 Python으로 구현합니다.  
화면 버퍼 관리와 ANSI/VT100 이스케이프 시퀀스 처리를 담당합니다.

### 작업 항목
- [ ] `pyte.Screen` + `pyte.ByteStream`으로 VT100 화면 버퍼 구현
  - `RealBuffer` (C++) → `pyte.Screen` (Python) 대응
  - `ConAnsi` (C++) → `pyte.ByteStream` (Python) 대응
- [ ] PTY 출력 → pyte 스트림 → 화면 버퍼 업데이트 루프 구현
- [ ] 화면 버퍼 변경 감지 (`dirty` 셀 추적)
- [ ] `VirtualConsole` 클래스 구현
  - 화면 셀 배열 (문자 + 전경색 + 배경색 + 속성)
  - 커서 위치 추적
  - 스크롤 처리

### 성공 기준
- `ls` / `dir` 명령어 실행 시 출력 결과가 화면 버퍼에 정상적으로 파싱됨
- 색상 코드(`\033[31m` 등)가 올바르게 처리됨
- 커서 위치가 정확히 추적됨

---

## 3단계: GUI 렌더링 구현 (Rendering Layer)

**목표:** `CVirtualConsole::Paint()` 역할을 구현합니다.  
화면 버퍼를 실제로 창에 그립니다.

### 작업 항목
- [ ] `QWidget` 기반 커스텀 터미널 뷰 위젯 구현 (`TerminalView`)
  - `paintEvent()`에서 `QPainter`로 각 셀 렌더링
  - 폰트: `QFont` + 고정폭(monospace) 폰트
  - 전경/배경색: `QPen` / `QBrush`
  - 커서 렌더링
- [ ] 폰트 메트릭 계산 (셀 크기 = 폰트 너비 × 폰트 높이)
- [ ] 창 크기 변경 시 열/행 수 자동 재계산 → PTY 크기 업데이트
- [ ] ANSI 256색 / 트루컬러 지원
- [ ] 기본 색상 팔레트 구현 (16 ANSI 색상)
- [ ] 선택/복사 기능 (마우스 드래그)

### 성공 기준
- 터미널 창에 색상 있는 텍스트가 렌더링됨
- 창 크기 변경 시 텍스트 줄 바꿈이 재조정됨
- 텍스트 드래그 선택 후 Ctrl+C 복사 가능

---

## 4단계: 탭 / UI 완성 (Multi-Tab & UI)

**목표:** `CVConGroup`, `CTabBarClass`, `CStatus` 역할을 구현합니다.  
멀티탭 지원과 전체 UI를 완성합니다.

### 작업 항목
- [ ] `QTabWidget` 또는 커스텀 탭 바 구현 (`CTabBarClass` 대응)
  - 탭 추가 / 제거 / 이름 변경
  - 드래그&드롭 탭 재정렬
- [ ] 멀티 탭 콘솔 관리 (`CVConGroup` 대응)
  - 탭마다 독립적인 `VirtualConsole` + PTY 프로세스
  - 탭 전환 시 포커스 이동
- [ ] 분할 창 (Split Pane) 기본 구현 (`QSplitter`)
- [ ] 상태 바 구현 (`CStatus` 대응)
  - 현재 디렉토리, 프로세스 이름 표시
- [ ] 단축키 시스템 구현 (`CConEmuCtrl` 대응)
  - `QShortcut` 기반 단축키 등록
  - `Ctrl+T`: 새 탭, `Ctrl+W`: 탭 닫기, `Alt+숫자`: 탭 전환
- [ ] 시스템 트레이 아이콘 (`QSystemTrayIcon`)
- [ ] 우클릭 컨텍스트 메뉴

### 성공 기준
- 멀티탭 생성/전환/닫기 가능
- 각 탭이 독립적인 쉘 세션 유지
- 분할 창에서 동시에 두 터미널 표시 가능

---

## 5단계: 설정 / 고급 기능 / 테스트 (Polish & Testing)

**목표:** 설정 시스템, 고급 기능, 그리고 종합 테스트를 완성합니다.

### 작업 항목
- [ ] 설정 시스템 구현 (`SettingsStorage`, `CSettings` 대응)
  - `config.xml` 또는 `config.json`에 설정 저장/로드
  - 폰트, 색상 팔레트, 단축키 설정 가능
- [ ] 설정 다이얼로그 구현 (각 `SetPg*` 대응)
  - 폰트 설정 탭
  - 색상 팔레트 탭
  - 단축키 탭
  - 일반 설정 탭
- [ ] 검색 기능 (Find in terminal, `CFindDlg` 대응)
- [ ] 스크롤백 버퍼 (스크롤 히스토리)
- [ ] 붙여넣기 확인 다이얼로그 (멀티라인 붙여넣기 경고)
- [ ] 자동 업데이트 확인 (선택)
- [ ] 단위 테스트 작성 (`pytest`)
  - 터미널 버퍼 파싱 테스트
  - 설정 로드/저장 테스트
  - 탭 관리 테스트
- [ ] 통합 테스트: 실제 명령어 실행 및 출력 검증

### 성공 기준
- 설정을 저장하고 재시작 시 복원됨
- 터미널 내에서 텍스트 검색 가능
- 전체 테스트 통과율 80% 이상
- 기본 터미널 사용 시나리오에서 안정적으로 동작

---

## 단계별 일정 요약

| 단계 | 핵심 결과물 | 테스트 방법 |
|---|---|---|
| 1단계 | 빈 창 + 쉘 프로세스 실행 | `echo hello` 입출력 확인 |
| 2단계 | 터미널 버퍼 파싱 | `ls -la` 출력 파싱 검증 |
| 3단계 | 렌더링 완성 | 색상 텍스트 화면 표시 |
| 4단계 | 멀티탭 UI | 여러 탭 동시 사용 |
| 5단계 | 설정 + 테스트 | pytest 전체 통과 |

---

## 범위 외 (Python 변환에서 제외)

다음 기능들은 Windows 커널/시스템 수준 기능으로, Python 변환 범위에서 제외합니다:
- `ConEmuHk.dll`: DLL 주입 + IAT 후킹 (시스템 수준, Python에서 불가)
- `ConEmuCD.dll`: 콘솔 프로세스 내 서버 데몬 (PTY로 대체)
- FAR Manager 플러그인 연동
- DWM 투명 창 (Aero) 고급 효과
- 기타 Windows 전용 고급 기능

---

## 참고 오픈소스 프로젝트

Python/Qt 기반 터미널 에뮬레이터 참고 구현:
- **Terminology** (EFL 기반)
- **Konsole** (Qt/KDE 기반, C++)
- **Hyper** (Electron 기반, JS)
- **QTermWidget** - Qt 터미널 위젯 라이브러리 (Python 바인딩 존재)
  - `pip install qtermwidget` 대신 `QTermWidget` C++ 래퍼 사용 가능
