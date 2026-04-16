# ConEmu 사용 라이브러리 명세

> Python 변환 시 대응 라이브러리 매핑을 포함한 원본 C++ 라이브러리 분석 문서

---

## 1. Windows 시스템 API (Win32)

### 1.1 GUI / 창 관리
| Win32 API | 용도 | Python 대응 |
|---|---|---|
| `CreateWindowEx` / `RegisterClass` | 창 생성 및 등록 | `tkinter` / `PyQt6` / `wxPython` |
| `SetWindowPos` / `MoveWindow` | 창 크기/위치 변경 | `tkinter.geometry()` |
| `DefWindowProc` / `WndProc` | 메시지 처리 핸들러 | Qt `event()` / tkinter bind |
| `GetWindowRect` / `GetClientRect` | 창 영역 조회 | `winfo_width()` 등 |
| `ShowWindow` / `UpdateWindow` | 창 표시/갱신 | `.deiconify()` / `.update()` |
| `SendMessage` / `PostMessage` | 윈도우 메시지 전송 | Qt `QApplication.sendEvent()` |
| `SetFocus` / `GetFocus` | 포커스 관리 | `.focus_set()` |

### 1.2 GDI / 렌더링
| Win32 API | 용도 | Python 대응 |
|---|---|---|
| `TextOut` / `ExtTextOut` | 텍스트 렌더링 | `PIL` / `pygame` / Qt `QPainter` |
| `BitBlt` / `StretchBlt` | 비트맵 복사 | `PIL.ImageDraw` / Qt |
| `CreateFont` / `SelectObject` | 폰트 설정 | `PIL.ImageFont` / Qt `QFont` |
| `SetTextColor` / `SetBkColor` | 텍스트 색상 | Qt `QPen` / `QPalette` |
| `PatBlt` / `FillRect` | 영역 채우기 | `canvas.create_rectangle()` |
| `CreateCompatibleDC` / `CreateDIBSection` | 오프스크린 버퍼 | `PIL.Image` |

### 1.3 콘솔 API
| Win32 API | 용도 | Python 대응 |
|---|---|---|
| `ReadConsoleOutput` | 콘솔 화면 버퍼 읽기 | `pywin32.win32console` |
| `WriteConsoleInput` | 콘솔 입력 주입 | `pywin32.win32console` |
| `SetConsoleWindowInfo` | 콘솔 창 크기 변경 | `os.get_terminal_size()` |
| `GetConsoleScreenBufferInfo` | 버퍼 정보 조회 | `shutil.get_terminal_size()` |
| `CreateConsoleScreenBuffer` | 새 화면 버퍼 생성 | `pty` 모듈 (Unix) |
| `SetConsoleMode` | 콘솔 모드 설정 | `termios` (Unix) |

### 1.4 프로세스 / 스레드
| Win32 API | 용도 | Python 대응 |
|---|---|---|
| `CreateProcess` | 프로세스 생성 | `subprocess.Popen` |
| `OpenProcess` / `TerminateProcess` | 프로세스 제어 | `psutil` |
| `CreateThread` / `WaitForSingleObject` | 스레드 관리 | `threading.Thread` |
| `CreateEvent` / `SetEvent` | 이벤트 동기화 | `threading.Event` |
| `EnterCriticalSection` | 임계 구역 | `threading.Lock` |
| `VirtualAllocEx` / `WriteProcessMemory` | 프로세스 메모리 주입 | `ctypes` |

### 1.5 IPC (프로세스 간 통신)
| Win32 API | 용도 | Python 대응 |
|---|---|---|
| `CreateNamedPipe` / `ConnectNamedPipe` | Named Pipe 서버 | `socket` (Unix socket) / `multiprocessing.Pipe` |
| `TransactNamedPipe` / `CallNamedPipe` | Pipe 트랜잭션 | `socket.send` / `recv` |
| `CreateFileMapping` / `MapViewOfFile` | 공유 메모리 | `multiprocessing.shared_memory` / `mmap` |
| `DuplicateHandle` | 핸들 복제 | 직접 대응 없음 (`pywin32` 사용) |

---

## 2. 시스템 DLL / COM

| DLL | 용도 | Python 대응 |
|---|---|---|
| `dwmapi.dll` | DWM 창 컴포지팅 (Aero 유리 효과 등) | `ctypes.windll.dwmapi` |
| `shell32.dll` | 쉘 기능 (파일 아이콘, 런치 등) | `ctypes.windll.shell32` / `winshell` |
| `shlwapi.dll` | 경로/URL 유틸리티 | `os.path` |
| `comctl32.dll` | 공통 컨트롤 (ListView, TabCtrl 등) | Qt / tkinter ttk |
| `user32.dll` | 창 / 입력 관리 | `pywin32.win32gui` |
| `kernel32.dll` | 프로세스 / 파일 / 메모리 | `ctypes.windll.kernel32` |
| `gdi32.dll` | 그래픽 출력 | `PIL` / `pygame` / Qt |
| `psapi.dll` | 프로세스 정보 | `psutil` |
| `wininet.dll` | HTTP 통신 (업데이트 체크) | `urllib.request` / `requests` |
| `wtsapi32.dll` | 터미널 서비스 세션 정보 | `pywin32.win32ts` |

---

## 3. C++ 표준 라이브러리

| 기능 | C++ | Python |
|---|---|---|
| 동적 배열 | `MArray<T>` (커스텀) | `list` |
| 해시맵 | `MMap<K,V>` (커스텀) | `dict` |
| 문자열 | `CEStr` (커스텀 Unicode 래퍼) | `str` (기본 Unicode) |
| 스레드 동기화 | `MSection`, `MEvent` | `threading.Lock`, `threading.Event` |
| 스마트 포인터 | 커스텀 참조 카운터 | Python GC (자동) |
| 파일 로그 | `MFileLog`, `MFileLogEx` | `logging` 모듈 |

---

## 4. XML 처리

| 원본 | 용도 | Python 대응 |
|---|---|---|
| `XmlLite` (COM) | 설정 파일(ConEmu.xml) 읽기/쓰기 | `xml.etree.ElementTree` / `lxml` |
| `WRegistry` | 레지스트리 기반 설정 | `winreg` |

---

## 5. 암호화 / 해싱

| 원본 | 용도 | Python 대응 |
|---|---|---|
| `crc32.h` (커스텀) | CRC32 체크섬 | `binascii.crc32` / `zlib.crc32` |
| `md5.cpp` (커스텀) | MD5 해시 | `hashlib.md5` |

---

## 6. Python 변환 시 추천 라이브러리 스택

### GUI 프레임워크
```
권장: PyQt6 (또는 PySide6)
  - 강력한 위젯 / 커스텀 페인팅 지원
  - QTermWidget (터미널 위젯 기존 구현 존재)
  - 탭, 분할 창, 드래그&드롭 등 모두 지원

대안: tkinter (간단하지만 기능 제한)
대안: wxPython (크로스 플랫폼 우수)
```

### 터미널 에뮬레이션
```
권장: pyte (Python 터미널 에뮬레이터 라이브러리)
  - VT100/VT220/xterm 이스케이프 시퀀스 파싱
  - 화면 버퍼 유지
  pip install pyte

보조: ptyprocess (Unix) / winpty (Windows)
  - PTY(Pseudo Terminal) 생성/관리
  pip install ptyprocess
  pip install pywinpty  # Windows
```

### 프로세스 관리
```
권장: subprocess (표준 라이브러리)
보조: psutil (프로세스 목록/정보)
  pip install psutil
```

### Windows 전용 (Windows에서 실행 시)
```
pywin32 - Windows API 접근
  pip install pywin32

pywinpty - Windows PTY 지원
  pip install pywinpty

ctypes - DLL/시스템 API 직접 호출 (표준 라이브러리)
```

### 설정 파일
```
표준: xml.etree.ElementTree (내장)
고급: lxml (더 빠름)
  pip install lxml
```

### 비동기 통신 (파이프/소켓)
```
표준: asyncio + asyncio.subprocess
보조: multiprocessing
```

### 테스트
```
pytest (단위 테스트)
  pip install pytest
```

---

## 7. 최소 requirements.txt (예상)

```
PyQt6>=6.5.0          # GUI 프레임워크
pyte>=0.8.0           # 터미널 에뮬레이터
psutil>=5.9.0         # 프로세스 관리
pywin32>=305; sys_platform=='win32'     # Windows API
pywinpty>=2.0.0; sys_platform=='win32'  # Windows PTY
lxml>=4.9.0           # XML 파싱 (선택)
```
