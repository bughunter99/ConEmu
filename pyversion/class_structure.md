# ConEmu 내부 클래스 구조 명세

> 본 문서는 ConEmu C++ 소스코드 분석을 기반으로 Python 변환을 위해 작성된 클래스 구조 명세입니다.

---

## 1. 주요 실행 파일 및 모듈 구성

ConEmu는 여러 개의 독립 실행파일 / DLL로 구성된 멀티 프로세스 아키텍처입니다.

| 모듈명 | 파일 | 역할 |
|---|---|---|
| ConEmu | `ConEmu.exe` | 메인 GUI 애플리케이션 (터미널 창) |
| ConEmuC | `ConEmuC.exe` / `ConEmuC64.exe` | 콘솔 헬퍼 / 다운로더 유틸리티 |
| ConEmuCD | `ConEmuCD.dll` / `ConEmuCD64.dll` | 콘솔 서버 데몬 (콘솔 프로세스 내 주입) |
| ConEmuHk | `ConEmuHk.dll` / `ConEmuHk64.dll` | API 후킹 DLL (Windows API 가로채기) |
| ConEmuBg | `ConEmuBg.exe` | 배경 화면 모듈 |
| ConEmuLn | `ConEmuLn.exe` | 런처 (ConEmu 실행 도우미) |
| ConEmuTh | `ConEmuTh.dll` | 테마/아이콘 모듈 |
| ConEmuPlugin | `ConEmuPlugin.dll` | FAR Manager 플러그인 |
| common | (정적 라이브러리) | 공통 유틸리티 (모든 모듈이 공유) |

---

## 2. 핵심 클래스 계층도 (ConEmu.exe)

```
CConEmuMain                          ← 메인 윈도우 클래스
  ├── CDwmHelper                     ← Windows DWM 컴포지팅 처리
  ├── CTaskBar                       ← Windows 작업 표시줄 연동
  ├── CFrameHolder                   ← 창 프레임 관리
  ├── CGestures                      ← 터치/제스처 입력 처리
  └── CConEmuCtrl                    ← 단축키 / 컨트롤 처리

CVirtualConsole                      ← 가상 콘솔 (탭 하나)
  ├── CVConRelease                   ← 참조 카운트 / 생명주기 관리
  └── CConEmuChild                   ← 자식 창 기반 클래스

CVConGroup                           ← 가상 콘솔 그룹 (Split 등)
  └── CVirtualConsole[]              ← 소속 가상 콘솔 목록

CRealConsole                         ← 실제 콘솔 프로세스 관리
  ├── CConEmuPipe                    ← GUI ↔ 서버 파이프 통신
  └── RealBuffer                     ← 콘솔 화면 버퍼

CTabBarClass                         ← 탭 바 UI
  └── CTabID[]                       ← 각 탭 정보

CStatus                              ← 상태 바 UI
CConEmuMenu                          ← 컨텍스트 / 시스템 메뉴
CConEmuInside                        ← 내부 모드 (다른 앱에 임베딩)
CDefaultTerminal                     ← 기본 터미널 등록/관리
CRunQueue                            ← 실행 큐 (프로세스 생성 관리)
GlobalHotkeys                        ← 전역 단축키 등록
CFontMgr                             ← 폰트 관리자
CBackground                          ← 배경 이미지 관리
CDragDrop                            ← 드래그&드롭
CUpdate                              ← 자동 업데이트
```

---

## 3. 핵심 클래스 상세 설명

### 3.1 `CConEmuMain` (src/ConEmu/ConEmu.h)
메인 GUI 창을 관리하는 최상위 클래스.

| 주요 멤버 변수 | 타입 | 설명 |
|---|---|---|
| `mp_Menu` | `CConEmuMenu*` | 메뉴 관리 객체 |
| `mp_TabBar` | `CTabBarClass*` | 탭 바 객체 |
| `mp_Status` | `CStatus*` | 상태 바 객체 |
| `mp_DefTrm` | `CDefaultTerminal*` | 기본 터미널 관리 |
| `mp_RunQueue` | `CRunQueue*` | 프로세스 실행 큐 |
| `mp_DragDrop` | `CDragDrop*` | 드래그&드롭 처리 |
| `mp_AttachDlg` | `CAttachDlg*` | 프로세스 연결 다이얼로그 |
| `mp_Inside` | `CConEmuInside*` | 내부 모드 관리 |

| 주요 메서드 | 설명 |
|---|---|
| `WinMain()` | 애플리케이션 진입점 |
| `Init()` | 창 초기화 |
| `MessageLoop()` | Windows 메시지 루프 |
| `ProcessHotKey()` | 단축키 처리 |
| `OnPaint()` | 화면 렌더링 |
| `CreateVCon()` | 새 가상 콘솔 생성 |

---

### 3.2 `CVirtualConsole` (src/ConEmu/VirtualConsole.h)
하나의 탭/콘솔 인스턴스를 나타내는 클래스.

| 주요 멤버 변수 | 타입 | 설명 |
|---|---|---|
| `mp_RCon` | `CRealConsole*` | 실제 콘솔 프로세스 연결 |
| `mp_ConEmu` | `CConEmuMain*` | 메인 윈도우 참조 |
| `mn_Flags` | `VConFlags` | 활성/보임/최대화 등 상태 플래그 |
| `mn_ID` | `int` | 고유 ID |
| `m_Sizes` | `VConRConSizes` | 크기 정보 (텍스트 셀, 픽셀 등) |

---

### 3.3 `CRealConsole` (src/ConEmu/RealConsole.h)
실제 콘솔 프로세스(cmd.exe, bash 등)와의 연결을 관리.

- `CConEmuPipe`를 통해 ConEmuCD 서버 프로세스와 Named Pipe로 통신
- 콘솔 화면 버퍼(`RealBuffer`)를 읽어 `CVirtualConsole`에 전달
- 프로세스 목록, FAR Manager 플러그인 상태 추적

---

### 3.4 `CVConGroup` (src/ConEmu/VConGroup.h)
가상 콘솔들을 그룹으로 관리 (분할 화면, 다중 탭 등).

| 정적 메서드 | 설명 |
|---|---|
| `GetActiveVCon()` | 현재 활성 콘솔 반환 |
| `GetVConFromTab()` | 탭 인덱스로 콘솔 조회 |
| `CloseVCon()` | 콘솔 닫기 |
| `SwitchNextTab()` | 다음 탭으로 전환 |

---

### 3.5 `ConEmuSrv` (src/ConEmuCD/ConEmuSrv.h)
콘솔 서버 프로세스 내에서 실행되는 데몬 객체.

- 콘솔 버퍼를 읽고 ConEmu GUI로 전송
- ANSI/VT100 이스케이프 시퀀스 처리 (`ConAnsi`)
- 프로세스 추적 (`ConProcess`)
- 콘솔 입력 이벤트 처리 (`ConEmuCmd`)

---

### 3.6 옵션/설정 클래스 (src/ConEmu/Options.h)

| 클래스 | 설명 |
|---|---|
| `SettingsStorage` | XML / 레지스트리에서 설정 로드/저장 |
| `CSettings` | 전체 설정값 구조체 |
| `SetPg*` | 각 설정 탭 페이지 (Fonts, Colors, Keys 등) |

---

### 3.7 공통 유틸리티 클래스 (src/common/)

| 클래스/구조체 | 설명 |
|---|---|
| `CEStr` | Unicode 문자열 래퍼 |
| `CmdLine` | 커맨드라인 파싱 |
| `MArray<T>` | 커스텀 동적 배열 |
| `MMap<K,V>` | 커스텀 해시맵 |
| `MPipe` | Named Pipe 래퍼 |
| `MFileMapping` | 공유 메모리 래퍼 |
| `MSection` | Critical Section / Mutex 래퍼 |
| `MEvent` | Windows Event 래퍼 |
| `WRegistry` | 레지스트리 접근 래퍼 |
| `WConsole` | Windows 콘솔 API 래퍼 |
| `WFiles` | 파일 시스템 유틸리티 |
| `EnvVar` | 환경 변수 관리 |

---

## 4. ConEmuHk.dll 주요 후킹 클래스 (src/ConEmuHk/)

| 파일 | 후킹 대상 |
|---|---|
| `hkConsole.cpp` | WriteConsoleOutput, ReadConsoleInput 등 |
| `hkConsoleOutput.cpp` | 콘솔 출력 관련 API |
| `hkConsoleInput.cpp` | 콘솔 입력 관련 API |
| `hkKernel.cpp` | CreateProcess, LoadLibrary 등 |
| `hkGDI.cpp` | GDI 그리기 함수 |
| `hkProcess.cpp` | 프로세스/스레드 API |
| `hkWindow.cpp` | 창 관련 API |
| `Ansi.cpp` | ANSI 이스케이프 처리 |
| `SetHook.cpp` | IAT 패치 기반 훅 설치 |
