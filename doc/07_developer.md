# 7. 개발자 가이드

## 7.1 프로젝트 구조

```
ConEmu/
├── pyversion/                  ← Python 구현 루트
│   ├── main.py                 ← 애플리케이션 진입점
│   ├── app.py                  ← 메인 창 (ConEmuApp)
│   ├── requirements.txt        ← 의존 라이브러리
│   │
│   ├── gui/                    ← GUI 모듈
│   │   ├── __init__.py
│   │   ├── terminal_view.py    ← 터미널 렌더링 위젯 (핵심)
│   │   └── settings_dialog.py  ← 설정 다이얼로그
│   │
│   ├── config/                 ← 설정 관리 모듈
│   │   ├── __init__.py
│   │   └── settings.py         ← AppSettings 싱글턴
│   │
│   ├── terminal/               ← 터미널 에뮬레이션 (확장 예정)
│   │   └── __init__.py
│   │
│   ├── ipc/                    ← 프로세스 간 통신 (확장 예정)
│   │   └── __init__.py
│   │
│   └── tests/                  ← 단위 테스트
│       ├── __init__.py
│       └── test_terminal_buffer.py
│
├── doc/                        ← 문서 (이 폴더)
│   ├── README.md
│   ├── 01_overview.md
│   ├── 02_installation.md
│   ├── 03_architecture.md
│   ├── 04_modules.md
│   ├── 05_configuration.md
│   ├── 06_shortcuts.md
│   ├── 07_developer.md         ← 이 파일
│   └── 08_faq.md
│
├── src/                        ← 원본 ConEmu C++ 소스
└── Release/                    ← 빌드 결과물
```

---

## 7.2 개발 환경 설정

```bash
# 1. 저장소 클론
git clone https://github.com/bughunter99/ConEmu.git
cd ConEmu

# 2. Python 가상환경 생성
python -m venv pyversion/.venv

# 3. 가상환경 활성화
# Linux/macOS
source pyversion/.venv/bin/activate
# Windows
pyversion\.venv\Scripts\activate

# 4. 개발용 의존성 설치
pip install -r pyversion/requirements.txt
pip install pytest

# 5. 실행하여 확인
cd pyversion
python main.py
```

---

## 7.3 코드 구조 규칙

### 로그 출력 규칙

모든 주요 동작에는 `[LOG]`, `[WARN]`, `[ERROR]` 접두사 로그가 있습니다.

```python
# 형식: [레벨][모듈/메서드명] 메시지
print(f"[LOG][start] 호출 — 플랫폼={sys.platform}, _running={self._running}")
print(f"[WARN][_write] _pty가 None이라 쓰기 불가")
print(f"[ERROR][_feed] pyte stream.feed 실패: {type(e).__name__}: {e}")
```

| 접두사 | 의미 |
|---|---|
| `[LOG]` | 일반 정보 로그 |
| `[WARN]` | 경고 (동작에는 영향 없음) |
| `[ERROR]` | 오류 (동작에 영향 있음) |

### C++ 대응 주석

각 클래스/메서드에는 원본 C++ 클래스 대응 정보를 주석으로 표시합니다.

```python
class TerminalView(QWidget):
    """
    터미널 뷰 위젯.
    CVirtualConsole (C++) 대응.
    """

def start(self):
    """터미널 프로세스 시작 (CRealConsole::Start() 대응)"""
```

---

## 7.4 새 설정 항목 추가하기

새로운 설정 항목을 추가하는 단계입니다.

### 1단계: `config/settings.py`에 기본값 추가

```python
_DEFAULTS: dict[str, Any] = {
    # 기존 섹션에 새 키 추가
    "general": {
        ...
        "my_new_option": True,    # 새 옵션 추가
    },
}
```

### 2단계: 프로퍼티 추가

```python
class AppSettings:
    @property
    def my_new_option(self) -> bool:
        return bool(self._get("general", "my_new_option"))

    @my_new_option.setter
    def my_new_option(self, v: bool) -> None:
        self._set("general", "my_new_option", bool(v))
```

### 3단계: `gui/settings_dialog.py`에 UI 추가

해당 페이지 클래스의 `_build_ui()` 메서드와 `load()`/`apply()` 메서드에 위젯을 추가합니다.

```python
class _GeneralPage(QWidget):
    def _build_ui(self):
        ...
        self._my_checkbox = QCheckBox("새 옵션")
        layout.addWidget(self._my_checkbox)

    def load(self, s: AppSettings):
        ...
        self._my_checkbox.setChecked(s.my_new_option)

    def apply(self, s: AppSettings):
        ...
        s.my_new_option = self._my_checkbox.isChecked()
```

---

## 7.5 새 기능 구현 가이드

### 텍스트 선택/복사 구현 (예시)

현재 미구현인 텍스트 선택 기능을 추가하려면:

1. `TerminalView`에 선택 영역 상태 변수 추가
   ```python
   self._sel_start: tuple[int, int] | None = None  # (row, col)
   self._sel_end: tuple[int, int] | None = None
   ```

2. `mousePressEvent`, `mouseMoveEvent`, `mouseReleaseEvent` 구현
   ```python
   def mousePressEvent(self, event: QMouseEvent):
       col = event.position().x() // self._cell_w
       row = event.position().y() // self._cell_h
       self._sel_start = (int(row), int(col))
       self._sel_end = None
   ```

3. `paintEvent`에서 선택 영역 하이라이트 추가

4. `_has_selection()` 메서드 업데이트
   ```python
   def _has_selection(self) -> bool:
       return self._sel_start is not None and self._sel_end is not None
   ```

5. Ctrl+Shift+C 시 클립보드 복사 처리 추가

---

## 7.6 테스트 작성 가이드

### 기존 테스트 실행

```bash
cd pyversion
pytest tests/ -v
```

### 새 테스트 추가

```python
# tests/test_settings.py

def test_settings_default():
    """설정 기본값 확인"""
    from config.settings import AppSettings
    # 싱글턴 초기화 (테스트 독립성을 위해 새 인스턴스 사용)
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_path = f.name
    os.unlink(tmp_path)  # 파일 없는 상태로 테스트

    s = AppSettings(config_file=tmp_path)
    assert s.font_size == 12
    assert s.font_bold == False
    assert s.cursor_style == "block"
```

### 테스트 파일 배치 규칙

- `tests/test_*.py` 형식으로 파일명 작성
- 함수명은 `test_*` 형식
- GUI 의존 테스트는 PyQt6 초기화가 필요할 수 있으므로 `QApplication` 픽스처 사용

---

## 7.7 5단계 개발 로드맵

현재 프로젝트는 **1단계(프로토타입)**가 구현된 상태입니다.

### 2단계: 터미널 에뮬레이터 코어 강화

- [ ] 256색 / 트루컬러 지원
- [ ] 스크롤백 버퍼 (histrory 스크롤)
- [ ] 텍스트 선택 및 클립보드 복사
- [ ] `terminal/` 모듈에 VirtualConsole 클래스 분리

### 3단계: GUI 렌더링 완성

- [ ] 마우스 드래그 선택 영역 렌더링
- [ ] 스크롤바 지원
- [ ] 배경 이미지 지원 (`CBackground` 대응)
- [ ] 더블클릭 단어 선택

### 4단계: 멀티탭 UI 완성

- [ ] 분할 창 (QSplitter)
- [ ] 탭 제목 동적 갱신 (OSC 시퀀스)
- [ ] 시스템 트레이 아이콘
- [ ] 우클릭 컨텍스트 메뉴

### 5단계: 고급 기능 + 테스트

- [ ] 터미널 내 텍스트 검색 (`CFindDlg` 대응)
- [ ] 멀티라인 붙여넣기 경고
- [ ] 전체 테스트 커버리지 80% 이상
- [ ] 패키징 (PyInstaller 등)

---

## 7.8 디버깅 팁

### 로그 확인

실행 시 콘솔에 출력되는 `[LOG]` 메시지를 통해 각 단계의 동작을 확인할 수 있습니다.

```bash
# 로그를 파일로 저장
python main.py 2>&1 | tee debug.log
```

### PTY 문제 디버깅

```python
# terminal_view.py의 _read_loop_unix 에서 상세 로그 확인
# 수신되는 바이트를 hex로 출력하여 ANSI 시퀀스 확인 가능
print(f"[DEBUG] 수신 hex: {data.hex()}")
```

### pyte 버퍼 상태 확인

```python
# paintEvent 안에서 임시 디버깅
if self._screen:
    for row in range(min(3, self._screen.lines)):
        line = "".join(self._screen.buffer[row][col].data
                       for col in range(min(40, self._screen.columns)))
        print(f"[DEBUG] row {row}: {line!r}")
```

---

## 7.9 관련 문서 / 참고 자료

- [PyQt6 공식 문서](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [pyte 공식 문서](https://pyte.readthedocs.io/)
- [ptyprocess 공식 문서](https://ptyprocess.readthedocs.io/)
- [VT100 / ANSI 이스케이프 시퀀스 표](https://vt100.net/docs/vt100-ug/chapter3.html)
- [원본 ConEmu 소스코드](https://github.com/Maximus5/ConEmu)
- [pyversion/class_structure.md](../pyversion/class_structure.md) — 원본 C++ 클래스 구조 명세
- [pyversion/data_flow.md](../pyversion/data_flow.md) — 원본 ConEmu 데이터 흐름 분석
- [pyversion/conversion_plan.md](../pyversion/conversion_plan.md) — 5단계 변환 계획
- [pyversion/libraries.md](../pyversion/libraries.md) — C++ ↔ Python 라이브러리 매핑
