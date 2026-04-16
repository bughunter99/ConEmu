# 2. 설치 및 실행 방법

## 2.1 시스템 요구사항

| 항목 | 최소 요구사항 |
|---|---|
| Python | 3.10 이상 (타입 힌트 `X \| Y` 문법 사용) |
| 운영체제 | Windows 10+, Ubuntu 20.04+, macOS 12+ |
| 화면 | 800 × 600 이상 |

> **Python 버전 확인:**
> ```bash
> python --version
> # Python 3.10.x 이상이어야 합니다
> ```

---

## 2.2 의존 라이브러리

`pyversion/requirements.txt` 파일에 모든 의존성이 정의되어 있습니다.

```
PyQt6>=6.5.0                              # GUI 프레임워크 (모든 플랫폼)
pyte>=0.8.0                               # 터미널 에뮬레이터 코어 (모든 플랫폼)
psutil>=5.9.0                             # 프로세스 관리 (모든 플랫폼)
ptyprocess>=0.7.0; sys_platform != "win32"  # Unix PTY (Linux/macOS)
pywinpty>=2.0.0;  sys_platform == "win32"   # Windows PTY
pywin32>=305;     sys_platform == "win32"   # Windows API
```

### 라이브러리 역할 설명

| 라이브러리 | 역할 | 플랫폼 |
|---|---|---|
| `PyQt6` | 창, 위젯, 이벤트, 렌더링(QPainter) | 전체 |
| `pyte` | VT100/ANSI 이스케이프 시퀀스 파싱, 화면 버퍼 관리 | 전체 |
| `psutil` | 실행 중인 프로세스 목록 조회, 종료 | 전체 |
| `ptyprocess` | Linux/macOS에서 가상 터미널(PTY) 생성 | Linux/macOS |
| `pywinpty` | Windows에서 가상 터미널(WinPTY) 생성 | Windows |
| `pywin32` | Windows 레지스트리, 콘솔 API 접근 | Windows |

---

## 2.3 설치 방법

### 방법 1: pip (권장)

```bash
# 저장소 클론
git clone https://github.com/bughunter99/ConEmu.git
cd ConEmu/pyversion

# 가상환경 생성 (권장)
python -m venv .venv

# 가상환경 활성화
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 방법 2: 플랫폼별 직접 설치

**Linux/macOS:**
```bash
pip install PyQt6 pyte psutil ptyprocess
```

**Windows:**
```bash
pip install PyQt6 pyte psutil pywinpty pywin32
```

---

## 2.4 실행 방법

```bash
# pyversion 디렉터리에서 실행
cd pyversion
python main.py
```

실행하면 다음과 같은 동작이 발생합니다:

1. PyQt6 애플리케이션 초기화
2. `AppSettings` 로드 (`~/.conemu-py/config.json` 읽기, 없으면 기본값 사용)
3. 메인 창(`ConEmuApp`) 생성
4. 첫 번째 터미널 탭 자동 생성
5. 플랫폼에 맞는 쉘 프로세스 시작:
   - Windows: `cmd.exe` (또는 `%COMSPEC%` 환경변수)
   - Linux/macOS: `bash` (또는 `$SHELL` 환경변수)

### 시작 쉘 변경하기

**환경변수로 쉘 지정:**
```bash
# Linux/macOS
SHELL=/bin/zsh python main.py

# Windows
set COMSPEC=C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe
python main.py
```

**설정 파일로 쉘 지정 (`~/.conemu-py/config.json`):**
```json
{
  "general": {
    "startup_shell": "/bin/zsh"
  }
}
```

---

## 2.5 첫 실행 후 확인 사항

실행 시 콘솔에 상세 로그가 출력됩니다. 정상 실행 시 다음과 같은 메시지가 나타납니다:

```
[LOG][app.py] 모듈 로딩 완료
[LOG][ConEmuApp.__init__] 앱 창 생성 시작
[LOG][AppSettings.load] 파일 없음 — 기본값 사용: '/home/user/.conemu-py/config.json'
[LOG][new_tab] TerminalView 생성 완료
[LOG][_start_unix] PTY spawn 완료 — PID=12345, fd=5, closed=False
[LOG][_start_unix] 읽기 스레드 시작됨 — PTY-Reader-Unix
```

---

## 2.6 문제 해결

### `ModuleNotFoundError: No module named 'PyQt6'`

```bash
pip install PyQt6
```

### `ModuleNotFoundError: No module named 'pyte'`

```bash
pip install pyte
```

### Windows에서 PTY 오류

```bash
pip install pywinpty
```

`pywinpty`가 없어도 `subprocess.Popen` 폴백으로 동작하지만,  
완전한 터미널 기능(색상, 커서 제어)은 `pywinpty`가 필요합니다.

### Python 버전이 3.10 미만인 경우

```python
# 오류: TypeError: unsupported operand type(s) for |
# 원인: threading.Thread | None 같은 Python 3.10+ 타입 힌트 문법

# 해결: Python 3.10 이상으로 업그레이드
```

---

## 2.7 테스트 실행

```bash
cd pyversion
pip install pytest
pytest tests/ -v
```

정상 실행 시 출력 예시:
```
tests/test_terminal_buffer.py::test_pyte_import PASSED
tests/test_terminal_buffer.py::test_basic_screen PASSED
tests/test_terminal_buffer.py::test_ansi_color PASSED
tests/test_terminal_buffer.py::test_cursor_position PASSED
tests/test_terminal_buffer.py::test_newline PASSED
tests/test_terminal_buffer.py::test_screen_resize PASSED
```
