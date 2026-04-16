# 4. 모듈별 상세 설명

## 4.1 `main.py` — 진입점

**파일 위치:** `pyversion/main.py`  
**대응 C++:** `WinMain()` 함수

### 역할

- `QApplication` 생성 (Qt 이벤트 루프의 최상위 객체)
- `ConEmuApp` 창 생성 및 표시
- Qt 이벤트 루프 시작 (`app.exec()`)

### 코드 흐름

```python
app = QApplication(sys.argv)       # Qt 초기화
window = ConEmuApp()               # 메인 창 생성
window.show()                      # 창 표시
sys.exit(app.exec())               # 이벤트 루프 시작 (여기서 블로킹)
```

---

## 4.2 `app.py` — 메인 애플리케이션 창

**파일 위치:** `pyversion/app.py`  
**대응 C++:** `CConEmuMain` 클래스  
**클래스:** `ConEmuApp(QMainWindow)`

### 역할

- 메인 창(메뉴바, 탭 위젯, 상태 바) 구성
- 탭 관리 (생성/닫기/전환)
- 단축키 등록
- 설정 변경 이벤트 수신 및 반영
- 앱 종료 시 창 위치/크기 저장

### 주요 메서드

| 메서드 | 설명 |
|---|---|
| `__init__()` | UI 초기화, 설정 로드, 첫 번째 탭 생성 |
| `_init_ui()` | QTabWidget, QStatusBar 생성 |
| `_init_menu()` | 파일/편집/도움말 메뉴 구성 |
| `_init_shortcuts()` | Ctrl+T, Ctrl+W 등 단축키 등록 |
| `_apply_settings()` | AppSettings 값을 창 전체에 반영 |
| `new_tab()` | 새 TerminalView 생성 및 탭 추가 |
| `close_tab(index)` | 지정 탭 닫기 (마지막 탭이면 앱 종료) |
| `open_settings()` | SettingsDialog 열기 |
| `closeEvent(event)` | 앱 종료 시 모든 탭의 PTY 정리 |

### 탭 관리 로직

```
new_tab() 호출
  → TerminalView(parent=self) 생성
  → title_changed / process_exited 시그널 연결
  → tab_widget.addTab(view, "터미널")
  → view.start() 호출  ← 쉘 프로세스 시작
  → status_bar 메시지 갱신

close_tab(index) 호출
  → 탭이 1개면 앱 종료
  → view.stop() 호출  ← 쉘 프로세스 종료
  → tab_widget.removeTab(index)
```

---

## 4.3 `gui/terminal_view.py` — 터미널 뷰 위젯

**파일 위치:** `pyversion/gui/terminal_view.py`  
**대응 C++:** `CVirtualConsole` + `CVConChild` + `CRealConsole`  
**클래스:** `TerminalView(QWidget)`

### 역할

ConEmu-Py의 핵심 위젯입니다. 하나의 탭이 하나의 `TerminalView`에 해당합니다.

- PTY 프로세스 시작/종료
- PTY 출력을 pyte 버퍼에 공급
- pyte 버퍼를 QPainter로 렌더링
- 키보드/마우스 입력을 PTY에 전달
- 창 크기 변경 시 PTY 크기 동기화

### 주요 멤버 변수

| 변수 | 타입 | 설명 |
|---|---|---|
| `_screen` | `pyte.Screen` | 터미널 화면 버퍼 (행/열 문자 셀) |
| `_stream` | `pyte.ByteStream` | ANSI 바이트 스트림 파서 |
| `_pty` | `winpty.PTY` \| `PtyProcess` \| `Popen` | PTY 또는 서브프로세스 |
| `_reader_thread` | `threading.Thread` | PTY 출력 읽기 백그라운드 스레드 |
| `_running` | `bool` | 터미널 실행 중 여부 |
| `_font` | `QFont` | 현재 사용 중인 모노스페이스 폰트 |
| `_cell_w`, `_cell_h` | `int` | 문자 셀 크기 (픽셀) |
| `_cols`, `_rows` | `int` | 화면 열/행 수 (기본 80×24) |
| `_settings` | `AppSettings` | 설정 싱글턴 참조 |
| `_repaint_timer` | `QTimer` | 16ms 간격 화면 갱신 타이머 |

### PyQt6 시그널

| 시그널 | 타입 | 발생 시점 |
|---|---|---|
| `title_changed` | `str` | pyte가 OSC 타이틀 변경 감지 시 |
| `process_exited` | — | Reader 스레드가 EOF 감지 시 |

### PTY 초기화 흐름

```
start()
  ├── sys.platform == "win32"
  │     → _start_windows()
  │           ├── winpty.PTY(cols, rows) 생성 시도
  │           ├── 실패 시 subprocess.Popen fallback
  │           └── Reader Thread (_read_loop_windows) 시작
  │
  └── else (Linux/macOS)
        → _start_unix()
              ├── ptyprocess.PtyProcess.spawn([shell]) 시도
              ├── 실패 시 subprocess.Popen fallback
              └── Reader Thread (_read_loop_unix) 시작
```

### 렌더링 파이프라인

```
paintEvent(QPaintEvent) 호출
  │
  ├── QPainter 생성 + 폰트 설정
  ├── 전체 배경 fillRect(cfg_bg)
  │
  ├── _screen.buffer 순회 (모든 행/열)
  │     각 셀:
  │       fg = _resolve_color(char.fg, cfg_fg)
  │       bg = _resolve_color(char.bg, cfg_bg)
  │       배경색 fillRect()
  │       문자 drawText()
  │
  └── 커서 렌더링
        ├── block: fillRect(white) + 반전 문자
        ├── underline: fillRect(하단 2px)
        └── bar: fillRect(좌측 2px)
```

### 색상 처리 (`_resolve_color`)

pyte는 색상을 세 가지 형태로 반환합니다:

| pyte 반환 형태 | 예시 | 처리 방법 |
|---|---|---|
| `"default"` / `None` | 기본 색상 | `cfg_fg` 또는 `cfg_bg` 사용 |
| 색상명 문자열 | `"red"`, `"green"` | `PYTE_COLOR_NAMES` 딕셔너리로 hex 변환 |
| hex 문자열 | `"#ff0000"` | 그대로 `QColor(color)` |
| 정수 인덱스 | `0` ~ `255` | `ANSI_COLORS` 팔레트 참조 |

### 창 크기 변경 처리

```
resizeEvent(QResizeEvent) 호출
  → 픽셀 크기 ÷ 셀 크기 = 새 열/행 수
  → 변경 시:
      _resize_pty(w, h)     ← PTY에 새 크기 통보
      _screen.resize(h, w)  ← pyte 버퍼 크기 조정
```

---

## 4.4 `config/settings.py` — 설정 관리

**파일 위치:** `pyversion/config/settings.py`  
**대응 C++:** `SettingsStorage` + `CSettings`  
**클래스:** `AppSettings`  
**패턴:** 싱글턴 (Singleton)

### 역할

- 설정 파일(`~/.conemu-py/config.json`) 읽기/쓰기
- 설정 기본값 제공
- 각 설정 항목에 Python 프로퍼티로 접근

### 싱글턴 사용법

```python
from config.settings import AppSettings

s = AppSettings.instance()  # 항상 같은 인스턴스 반환
print(s.font_family)        # "Consolas"
s.font_size = 14            # 설정값 변경
s.save()                    # config.json 저장
```

### 설정 섹션 구조

```python
{
  "general":    { ... },   # 시작 쉘, 스크롤백, 종료 시 저장
  "fonts":      { ... },   # 폰트 패밀리, 크기, 굵기
  "colors":     { ... },   # 기본 FG/BG 색상, 16색 팔레트
  "appearance": { ... },   # 창 타이틀, 탭 위치, 탭 타이틀 포맷
  "cursor":     { ... },   # 커서 스타일, 깜빡임
  "keyboard":   { ... },   # 단축키 바인딩
  "window":     { ... },   # 창 크기, 위치, 최대화 여부
}
```

### 주요 프로퍼티 목록

| 프로퍼티 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `startup_shell` | `str` | `""` (OS 기본) | 시작 쉘 경로 |
| `scrollback_lines` | `int` | `9999` | 스크롤백 버퍼 줄 수 |
| `save_on_exit` | `bool` | `True` | 종료 시 자동 저장 |
| `font_family` | `str` | `"Consolas"` (Win) / `"Monospace"` (Linux) | 폰트 패밀리 |
| `font_size` | `int` | `12` | 폰트 크기 (pt) |
| `font_bold` | `bool` | `False` | 굵은 글꼴 |
| `default_fg` | `str` | `"#c0c0c0"` | 기본 전경색 (hex) |
| `default_bg` | `str` | `"#1e1e1e"` | 기본 배경색 (hex) |
| `palette` | `list[str]` | ConEmu 기본 16색 | ANSI 16색 팔레트 |
| `window_title` | `str` | `"ConEmu-Py"` | 창 제목 |
| `tab_position` | `str` | `"top"` | 탭 위치 (`"top"` / `"bottom"`) |
| `cursor_style` | `str` | `"block"` | 커서 스타일 |
| `cursor_blink` | `bool` | `True` | 커서 깜빡임 |
| `window_width` | `int` | `900` | 창 가로 크기 (px) |
| `window_height` | `int` | `600` | 창 세로 크기 (px) |
| `window_x` | `int` | `-1` | 창 X 위치 (-1: OS 기본) |
| `window_y` | `int` | `-1` | 창 Y 위치 (-1: OS 기본) |
| `window_maximized` | `bool` | `False` | 최대화 여부 |

---

## 4.5 `gui/settings_dialog.py` — 설정 다이얼로그

**파일 위치:** `pyversion/gui/settings_dialog.py`  
**대응 C++:** `CSettingsDlg` + 각 `SetPg*` 페이지 클래스

### 구성

좌측 페이지 목록 + 우측 설정 폼 구조 (원본 ConEmu 설정 창과 동일한 레이아웃).

| 페이지 | 클래스 | 설정 가능 항목 |
|---|---|---|
| General | `_GeneralPage` | 시작 쉘, 스크롤백 줄 수, 종료 시 저장 |
| Fonts | `_FontsPage` | 폰트 패밀리/크기/굵기, 미리보기 |
| Colors | `_ColorsPage` | 기본 FG/BG 색상, ANSI 16색 팔레트 편집 |
| Appearance | `_AppearancePage` | 창 타이틀, 탭 위치 (상/하) |
| Cursor | `_CursorPage` | 커서 스타일 (block/underline/bar), 깜빡임 |
| Keyboard | `_KeyboardPage` | 단축키 바인딩 목록 편집 |

### 설정 변경 콜백 시스템

```python
# SettingsDialog가 Apply 시 호출
_notify_settings_changed()
  → _change_callbacks 리스트의 모든 콜백 실행
  → ConEmuApp._apply_settings() 자동 호출
  → 모든 TerminalView.apply_settings() 자동 호출
```

```python
# 외부에서 콜백 등록
from gui.settings_dialog import register_settings_changed
register_settings_changed(my_callback)
```

---

## 4.6 `tests/test_terminal_buffer.py` — 단위 테스트

**파일 위치:** `pyversion/tests/test_terminal_buffer.py`  
**프레임워크:** pytest

### 테스트 목록

| 테스트 함수 | 검증 내용 |
|---|---|
| `test_pyte_import` | pyte 라이브러리 임포트 성공 여부 |
| `test_basic_screen` | 기본 텍스트 입력 → 버퍼 저장 확인 |
| `test_ansi_color` | `\033[31m` → `char.fg == "red"` 파싱 확인 |
| `test_cursor_position` | 문자 입력 후 커서 위치 추적 확인 |
| `test_newline` | `\r\n` 개행 처리 및 줄 이동 확인 |
| `test_screen_resize` | `screen.resize(h, w)` 크기 변경 확인 |

### 실행 방법

```bash
cd pyversion
pytest tests/ -v
```
