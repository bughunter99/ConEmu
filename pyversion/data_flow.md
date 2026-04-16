# ConEmu 데이터 흐름 명세

> Python 변환을 위한 ConEmu 내부 데이터 흐름 분석 문서

---

## 1. 전체 아키텍처 개요

ConEmu는 **멀티 프로세스 아키텍처**를 사용합니다. 주요 프로세스 간 통신은 **Named Pipe**와 **공유 메모리(FileMapping)**로 이루어집니다.

```
┌─────────────────────────────────────────────────────────────┐
│                    ConEmu.exe (GUI 프로세스)                  │
│                                                             │
│  CConEmuMain ──┬── CVConGroup ──── CVirtualConsole[]       │
│                │       └── CRealConsole ──── CConEmuPipe   │
│                ├── CTabBarClass                             │
│                ├── CStatus                                  │
│                └── CConEmuCtrl (단축키)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │  Named Pipe
                           │  (\\.\pipe\ConEmu\{GUID})
                           │
┌──────────────────────────▼──────────────────────────────────┐
│             ConEmuCD.dll (콘솔 서버, 각 콘솔에 주입)          │
│                                                             │
│  ConEmuSrv ──┬── ConData (콘솔 버퍼 캐시)                   │
│              ├── ConAnsi (ANSI 시퀀스 파싱)                  │
│              ├── ConProcess (프로세스 추적)                  │
│              └── Actions (명령 실행)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │  DLL 주입
                           │
┌──────────────────────────▼──────────────────────────────────┐
│         ConEmuHk.dll (후킹, 각 콘솔 프로세스에 주입)          │
│                                                             │
│  SetHook ──── hkConsole / hkKernel / hkGDI ...             │
│               (Windows API 인터셉트)                        │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│         실제 콘솔 프로세스 (cmd.exe, bash, PowerShell 등)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 프로세스 시작 흐름

```
WinMain()
  └── CConEmuMain::Init()
        ├── 설정 로드 (SettingsStorage: XML 또는 레지스트리)
        ├── 폰트 초기화 (CFontMgr)
        ├── 탭 바 생성 (CTabBarClass)
        ├── 상태 바 생성 (CStatus)
        ├── 전역 단축키 등록 (GlobalHotkeys)
        ├── 기본 터미널 설정 (CDefaultTerminal)
        └── 첫 번째 콘솔 생성
              └── CConEmuMain::CreateVCon()
                    ├── CVirtualConsole 객체 생성
                    ├── CRealConsole 생성
                    └── ConEmuCD 서버 프로세스 시작
                          └── Named Pipe 연결 수립
```

---

## 3. 콘솔 출력 데이터 흐름

```
실제 프로세스 (cmd.exe 등)
  │
  │  WriteConsole() / WriteFile() 호출
  ▼
ConEmuHk.dll 훅 (hkConsoleOutput.cpp)
  │  ANSI 이스케이프 처리 (Ansi.cpp)
  ▼
ConEmuCD.dll 서버 (ConEmuSrv)
  │  콘솔 버퍼 읽기 (ConData)
  │  화면 변경 감지 (diffing)
  ▼
Named Pipe 전송
  │  패킷: CESERVER_REQ (ConsoleMessages.h)
  ▼
CRealConsole (GUI 프로세스)
  │  버퍼 수신 및 캐시 갱신 (RealBuffer)
  ▼
CVirtualConsole::OnPaint()
  │  GDI/GDI+로 문자셀 렌더링
  ▼
화면 출력 (Windows HWND)
```

---

## 4. 키보드 입력 데이터 흐름

```
사용자 키 입력
  ▼
ConEmu 메인 창 WM_KEYDOWN / WM_KEYUP
  ▼
CConEmuCtrl::ProcessHotKeyMsg()
  ├── 전역 단축키 처리? → 해당 기능 실행 (탭 전환, 분할 등)
  └── 일반 키? ↓
        CRealConsole::ProcessKeyDown()
          ▼
        Named Pipe로 입력 전송 → ConEmuSrv
          ▼
        WriteConsoleInput() 호출 (실제 콘솔 프로세스로 전달)
```

---

## 5. 마우스 입력 데이터 흐름

```
사용자 마우스 클릭/이동
  ▼
ConEmu 메인 창 WM_LBUTTONDOWN 등
  ├── 탭 클릭? → CTabBarClass::OnClick()
  ├── 상태 바? → CStatus::OnClick()
  ├── 콘솔 영역? ↓
  │     CRealConsole::ProcessMouse()
  │       ▼
  │     Named Pipe → ConEmuSrv → WriteConsoleInput()
  └── 드래그? → CDragDrop 처리
```

---

## 6. IPC (프로세스 간 통신) 데이터 구조

### 6.1 Named Pipe 패킷 형식

파일: `src/common/ConsoleAnnotation.h`, `ConEmuInOut.h`

```
CESERVER_REQ (기본 요청 헤더)
  ├── cbSize    : DWORD  - 전체 패킷 크기
  ├── nCmd      : DWORD  - 명령 코드 (CECMD_*)
  ├── nSrcPID   : DWORD  - 발신 프로세스 ID
  └── Data[]    : 가변 길이 페이로드

CESERVER_REQ_SETBUFFERINFO  - 콘솔 버퍼 크기 변경
CESERVER_REQ_GETALL         - 전체 화면 버퍼 요청
CESERVER_REQ_GETALLTABS     - 탭 목록 요청
CESERVER_REQ_RUNDIRECT      - 명령 실행 요청
```

### 6.2 공유 메모리 구조

```
MFileMapping (src/common/MFileMapping.h)
  └── CESERVER_CONSOLE_MAPPING_HDR
        ├── 콘솔 크기 (행, 열)
        ├── 프로세스 PID 목록
        ├── Far Manager 정보
        └── 기타 상태 플래그
```

---

## 7. 설정 데이터 흐름

```
ConEmu 시작 시:
  SettingsStorage::Load()
    ├── XML 파일 (ConEmu.xml, XmlLite API)
    └── Windows 레지스트리 (WRegistry)
          ↓
    CSettings 구조체에 로드
          ↓
    각 컴포넌트에 분배 (Options.cpp)

설정 변경 시 (설정 다이얼로그):
  SetPg* 페이지 → CSettings 수정
          ↓
    SettingsStorage::Save()
```

---

## 8. 렌더링 파이프라인

```
CVirtualConsole::Paint()
  │
  ├── 폰트 정보 조회 (CFontMgr)
  ├── 색상 팔레트 조회 (SetColorPalette)
  │
  ├── 각 텍스트 셀 순회
  │     ├── 문자 코드 → 글리프 → GDI TextOut()
  │     └── 전경/배경 색 → GDI SetTextColor() / SetBkColor()
  │
  ├── 커서 그리기
  ├── 선택 영역 하이라이트
  └── 배경 이미지 (CBackground)
```

---

## 9. 탭 관리 흐름

```
탭 생성:
  CConEmuMain::CreateVCon()
    → CVConGroup::AddVCon()
    → CTabBarClass::UpdateTabs()

탭 전환:
  CConEmuCtrl (단축키) → CVConGroup::SwitchNextTab()
    → CVirtualConsole::Activate()
    → 화면 갱신

탭 닫기:
  CVConGroup::CloseVCon()
    → CRealConsole::Close()
    → Named Pipe 닫기
    → CTabBarClass::UpdateTabs()
```

---

## 10. 업데이트 흐름

```
CUpdate::CheckForUpdate()
  ├── HTTP 요청 (WinINet API)
  ├── 버전 비교
  └── ConEmuC.exe Downloader 호출
        └── 파일 다운로드 → 패치 적용
```
