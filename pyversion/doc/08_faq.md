# 8. 자주 묻는 질문 (FAQ) 및 트러블슈팅

## 자주 묻는 질문

---

### Q1. ConEmu-Py와 원본 ConEmu의 차이점은 무엇인가요?

| 항목 | 원본 ConEmu | ConEmu-Py |
|---|---|---|
| 구현 언어 | C++ | Python + PyQt6 |
| 플랫폼 | Windows 전용 | Windows, Linux, macOS |
| 성능 | 매우 빠름 (네이티브) | 비교적 느림 (인터프리터) |
| 기능 | 완전한 기능 | 핵심 기능만 (개발 중) |
| DLL 주입/API 후킹 | 지원 | 미지원 (PTY로 대체) |
| Far Manager 플러그인 | 지원 | 미지원 |

ConEmu-Py는 원본 ConEmu의 **완전한 대체품이 아닙니다**. 핵심 터미널 에뮬레이션 기능을 Python으로 학습하고 실험하는 목적으로 개발되고 있습니다.

---

### Q2. 실행했더니 창만 뜨고 터미널이 동작하지 않아요.

**원인 1: pyte가 설치되지 않은 경우**

화면에 "pyte 라이브러리가 필요합니다" 메시지가 나타납니다.

```bash
pip install pyte
```

**원인 2: PTY 라이브러리가 없는 경우**

콘솔 로그에 `[WARN] ptyprocess ImportError` 또는 `[WARN] pywinpty ImportError`가 출력됩니다.

```bash
# Linux/macOS
pip install ptyprocess

# Windows
pip install pywinpty
```

**확인 방법:** 실행 시 출력되는 `[LOG]` 로그에서 오류를 확인하세요.

---

### Q3. 한글 입력이 되지 않아요.

현재 1단계 프로토타입에서는 한글 입력(IME 조합 입력)이 지원되지 않습니다.  
`keyPressEvent`는 `event.text()`로 텍스트를 가져오는데, IME 조합 중에는 텍스트가 확정되지 않아 전달되지 않습니다.  
한글 입력 지원은 추후 단계에서 `QInputMethodEvent` 처리로 구현될 예정입니다.

---

### Q4. 창 크기를 늘려도 터미널이 맞게 늘어나지 않아요.

창 크기 변경 시 `resizeEvent`가 호출되어 PTY 크기와 pyte 버퍼가 자동으로 조정됩니다.  
단, PTY 라이브러리(`ptyprocess`, `pywinpty`)가 없어 `subprocess.Popen` 폴백으로 실행 중인 경우에는 PTY 크기 조정이 되지 않습니다.

```bash
# 완전한 창 크기 조정을 위해 PTY 라이브러리 설치 권장
pip install ptyprocess   # Linux/macOS
pip install pywinpty     # Windows
```

---

### Q5. Python 3.9에서 실행하면 오류가 납니다.

ConEmu-Py는 Python **3.10 이상**이 필요합니다.  
Python 3.10에서 추가된 타입 힌트 문법 (`X | Y`)을 사용하기 때문입니다.

```python
# 이 문법은 Python 3.10 이상에서만 동작
self._reader_thread: threading.Thread | None = None
```

Python 3.10 이상으로 업그레이드하세요.

---

### Q6. 색상이 이상하게 표시됩니다.

**원인 1: 폰트 렌더링 문제**

설정에서 폰트를 변경해 보세요 (Ctrl+, → Fonts).

**원인 2: ANSI 색상 이름 매핑 문제**

pyte가 색상을 `"brown"`으로 반환하는 경우가 있는데, 이는 황색 계열입니다.  
`PYTE_COLOR_NAMES` 딕셔너리에 `"brown": "#808000"` 매핑이 포함되어 있습니다.

**원인 3: 팔레트 설정 문제**

설정 파일에서 `colors.palette` 배열이 정확히 16개 항목인지 확인하세요.  
16개가 아니면 기본 팔레트로 대체됩니다.

---

### Q7. 탭을 많이 열면 느려집니다.

각 탭은 독립적인 쉘 프로세스와 Reader 스레드를 가집니다.  
또한, 화면 갱신 타이머가 16ms 간격으로 모든 탭의 렌더링을 요청합니다.  
탭이 많을수록 CPU 사용량이 증가합니다.

현재 1단계에서는 최적화가 이루어지지 않았으며, 추후 단계에서 inactive 탭의 렌더링을 억제하는 방식으로 개선할 예정입니다.

---

### Q8. 설정 파일이 저장되지 않아요.

**확인 사항:**

1. `save_on_exit`가 `true`인지 확인:
   ```json
   "general": { "save_on_exit": true }
   ```

2. `~/.conemu-py/` 디렉터리에 쓰기 권한이 있는지 확인:
   ```bash
   ls -la ~/.conemu-py/
   ```

3. 설정 다이얼로그에서 Apply 또는 OK를 눌렀는지 확인.

4. 콘솔 로그에서 `[LOG][AppSettings.save]` 또는 `[ERROR][AppSettings.save]` 메시지를 확인.

---

### Q9. `AttributeError: 'TerminalView' object has no attribute '_running'` 오류가 납니다.

이 오류는 `__init__` 메서드가 정상적으로 실행되지 않아 `_running` 변수가 초기화되지 않은 경우 발생합니다.  

원인은 `terminal_view.py`에서 `def __init__(self, parent=None):` 선언 줄이 누락된 경우입니다.  
최신 코드로 업데이트하거나, 해당 선언 줄이 `apply_settings()` 메서드 바로 아래에 올바르게 위치하는지 확인하세요.

```python
    def apply_settings(self, settings=None) -> None:
        ...
        self.update()

    def __init__(self, parent=None):   # ← 이 줄이 있어야 합니다
        print(f"[LOG][__init__] TerminalView 생성 시작 ...")
```

---

### Q10. Windows에서 cmd.exe 대신 PowerShell을 기본 쉘로 설정하고 싶어요.

방법 1 - 환경변수 설정:
```batch
set COMSPEC=C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe
python main.py
```

방법 2 - 설정 파일 수정 (`~/.conemu-py/config.json`):
```json
"general": {
  "startup_shell": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
}
```

방법 3 - 설정 다이얼로그: Ctrl+, → General → Startup Shell 항목에 경로 입력

---

## 트러블슈팅 체크리스트

실행 문제가 발생했을 때 순서대로 확인하세요:

- [ ] Python 버전이 3.10 이상인지 확인: `python --version`
- [ ] 의존성이 모두 설치되어 있는지 확인: `pip list | grep -E "PyQt6|pyte|ptyprocess|pywinpty"`
- [ ] `pyversion/` 디렉터리에서 실행 중인지 확인: `python main.py`
- [ ] 콘솔에 출력되는 `[ERROR]` 로그 확인
- [ ] 설정 파일이 올바른 JSON인지 확인: `python -c "import json; json.load(open('/home/user/.conemu-py/config.json'))"`
- [ ] 가상환경이 활성화되어 있는지 확인

---

## 오류 보고

버그를 발견하셨다면 다음 정보와 함께 GitHub 이슈를 등록해주세요:

1. 운영체제 및 버전
2. Python 버전 (`python --version`)
3. 설치된 라이브러리 버전 (`pip freeze`)
4. 오류 재현 방법
5. 콘솔 출력 로그 전체 (실행 시 출력되는 `[LOG]`/`[ERROR]` 메시지)
