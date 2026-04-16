# 1. 프로젝트 개요

## 1.1 ConEmu란?

[ConEmu](https://conemu.github.io)는 Windows 전용 고성능 터미널 에뮬레이터입니다.  
하나의 GUI 창 안에 여러 콘솔(탭)을 동시에 띄울 수 있으며, 탭, 분할 창, 풍부한 커스터마이징을 제공합니다.  
원본 C++ 코드베이스는 약 18만 줄 이상으로, Windows API(GDI, Named Pipe, DLL 주입 등)에 깊이 의존합니다.

### 원본 ConEmu의 주요 특징

- 탭 및 분할 창(Split Pane)
- Windows CMD, PowerShell, Git Bash, WSL 등 모든 콘솔 앱 지원
- Far Manager 전용 확장 기능
- 고급 폰트/색상/투명도 커스터마이징
- 전역 단축키 및 매크로
- DWM 투명 창(Aero Glass) 효과
- 자동 업데이트

---

## 1.2 ConEmu-Py란?

**ConEmu-Py**는 ConEmu의 핵심 기능을 **Python + PyQt6**으로 재구현하는 프로젝트입니다.

### 목표

| 목표 | 설명 |
|---|---|
| 크로스 플랫폼 | Windows뿐 아니라 Linux, macOS에서도 동작 |
| Python 기반 | C++ 없이 순수 Python으로 터미널 에뮬레이터 구현 |
| 학습/연구 | ConEmu 내부 구조를 Python으로 이해하고 실험 |
| 점진적 변환 | 5단계 계획에 따라 기능을 단계별로 구현 |

### 현재 구현 상태 (1단계 프로토타입)

| 기능 | 상태 |
|---|---|
| 기본 창 + 탭 | ✅ 구현 완료 |
| PTY 프로세스 실행 (Unix/Windows) | ✅ 구현 완료 |
| VT100/ANSI 터미널 버퍼 (pyte) | ✅ 구현 완료 |
| 커스텀 터미널 렌더링 (QPainter) | ✅ 구현 완료 |
| 설정 파일 (config.json) | ✅ 구현 완료 |
| 설정 다이얼로그 | ✅ 구현 완료 |
| 텍스트 선택/복사 | 🔲 미구현 (2단계 예정) |
| 분할 창(Split Pane) | 🔲 미구현 (4단계 예정) |
| 검색 기능 | 🔲 미구현 (5단계 예정) |
| DLL 주입 / API 후킹 | ❌ Python 변환 범위 외 |

---

## 1.3 원본 C++ 클래스 → Python 대응 구조

ConEmu-Py는 원본 ConEmu의 C++ 클래스 구조를 Python 모듈로 대응시킵니다.

| C++ (원본 ConEmu) | Python (ConEmu-Py) | 설명 |
|---|---|---|
| `CConEmuMain` | `ConEmuApp` (app.py) | 메인 애플리케이션 창 |
| `CVirtualConsole` | `TerminalView` (gui/terminal_view.py) | 터미널 뷰 위젯 |
| `CRealConsole` | `TerminalView._pty` + 읽기 루프 | PTY 프로세스 관리 |
| `CTabBarClass` | `QTabWidget` (app.py) | 탭 바 |
| `CStatus` | `QStatusBar` (app.py) | 상태 바 |
| `CConEmuCtrl` | `_init_shortcuts()` (app.py) | 단축키 처리 |
| `SettingsStorage` / `CSettings` | `AppSettings` (config/settings.py) | 설정 관리 |
| `SetPg*` (설정 탭 페이지) | `SettingsDialog` (gui/settings_dialog.py) | 설정 다이얼로그 |
| `RealBuffer` | `pyte.Screen` | 터미널 화면 버퍼 |
| `ConAnsi` | `pyte.ByteStream` | ANSI 이스케이프 파싱 |
| `CVConGroup` | `ConEmuApp._tabs` 리스트 | 탭 그룹 관리 |
| `CFontMgr` | `TerminalView._build_font_from_settings()` | 폰트 관리 |

---

## 1.4 기술 스택

| 분류 | 라이브러리 | 역할 |
|---|---|---|
| GUI 프레임워크 | [PyQt6](https://pypi.org/project/PyQt6/) | 창, 위젯, 이벤트 처리 |
| 터미널 에뮬레이션 | [pyte](https://pypi.org/project/pyte/) | VT100/ANSI 버퍼 관리 |
| Unix PTY | [ptyprocess](https://pypi.org/project/ptyprocess/) | Linux/macOS PTY 생성 |
| Windows PTY | [pywinpty](https://pypi.org/project/pywinpty/) | Windows PTY 생성 |
| 프로세스 관리 | [psutil](https://pypi.org/project/psutil/) | 프로세스 정보 조회 |
| Windows API | [pywin32](https://pypi.org/project/pywin32/) | Windows 전용 API 접근 |

---

## 1.5 라이선스

원본 ConEmu는 **BSD 3-Clause** 라이선스를 따릅니다.  
ConEmu-Py 역시 동일한 라이선스 조건 하에 제공됩니다.  
자세한 내용은 [`Release/ConEmu/License.txt`](../Release/ConEmu/License.txt)를 참조하세요.
