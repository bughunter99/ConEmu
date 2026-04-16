# 3. 전체 아키텍처

## 3.1 컴포넌트 구성도

```
┌──────────────────────────────────────────────────────────────┐
│                     ConEmu-Py 애플리케이션                     │
│                                                              │
│  main.py                                                     │
│    └── ConEmuApp (app.py)              ← 메인 창             │
│          ├── QMenuBar                  ← 파일/편집/도움말 메뉴 │
│          ├── QTabWidget                ← 탭 바               │
│          │     ├── TerminalView [0]    ← 탭 1 (터미널 위젯)  │
│          │     ├── TerminalView [1]    ← 탭 2                │
│          │     └── ...                                       │
│          ├── QStatusBar                ← 상태 바             │
│          └── AppSettings              ← 설정 싱글턴          │
│                                                              │
│  TerminalView (gui/terminal_view.py)   ← 각 탭의 핵심 위젯   │
│    ├── pyte.Screen                     ← 터미널 화면 버퍼     │
│    ├── pyte.ByteStream                 ← ANSI 파서           │
│    ├── PTY 프로세스                    ← 실제 쉘 프로세스     │
│    │     ├── [Windows] winpty.PTY      ← WinPTY              │
│    │     └── [Unix]    PtyProcess      ← POSIX PTY           │
│    ├── Reader Thread                   ← PTY 출력 읽기 스레드 │
│    └── QTimer (16ms)                   ← 60fps 화면 갱신     │
│                                                              │
│  AppSettings (config/settings.py)      ← 설정 관리자         │
│    └── ~/.conemu-py/config.json        ← 설정 파일           │
│                                                              │
│  SettingsDialog (gui/settings_dialog.py) ← 설정 다이얼로그   │
│    ├── General 페이지                                        │
│    ├── Fonts 페이지                                          │
│    ├── Colors 페이지                                         │
│    ├── Appearance 페이지                                     │
│    ├── Cursor 페이지                                         │
│    └── Keyboard 페이지                                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 3.2 데이터 흐름: 터미널 출력

쉘 프로세스의 출력이 화면에 표시되기까지의 흐름입니다.

```
[쉘 프로세스] (bash, cmd.exe 등)
      │
      │ PTY 출력 (바이트 스트림, ANSI 이스케이프 포함)
      ▼
[Reader Thread] (_read_loop_unix / _read_loop_windows)
      │  daemon 스레드로 백그라운드 실행
      │  PTY에서 최대 4096바이트씩 읽기
      ▼
[TerminalView._feed(data: bytes)]
      │
      │ pyte.ByteStream.feed(data)
      ▼
[pyte.ByteStream]  ← ANSI/VT100 이스케이프 파서
      │  \033[31m → 빨간색 속성 설정
      │  \033[A   → 커서 위로 이동
      │  일반 문자 → 현재 커서 위치에 저장
      ▼
[pyte.Screen]  ← 80×24 (또는 동적 크기) 문자 셀 배열
      │  screen.buffer[row][col].data  → 문자
      │  screen.buffer[row][col].fg    → 전경색
      │  screen.buffer[row][col].bg    → 배경색
      │  screen.cursor.x, .y           → 커서 위치
      ▼
[QTimer timeout → TerminalView.update()]
      │  16ms 간격 (약 60fps) 로 화면 갱신 요청
      ▼
[TerminalView.paintEvent(QPaintEvent)]
      │  QPainter 로 화면 버퍼 렌더링
      │  각 셀에 배경색 fillRect() + 텍스트 drawText()
      │  커서 렌더링 (block/underline/bar)
      ▼
[Qt 화면 출력]
```

---

## 3.3 데이터 흐름: 키보드 입력

사용자 키 입력이 쉘 프로세스에 전달되기까지의 흐름입니다.

```
[사용자 키보드 입력]
      │
      ▼
[Qt 이벤트 시스템]
      │
      ▼
[TerminalView.keyPressEvent(QKeyEvent)]
      │
      ├── 전역 단축키 확인 (Ctrl+T, Ctrl+W 등)
      │     → 해당 기능 실행 (새 탭, 탭 닫기)
      │     (이 경우 PTY에는 전달 안 됨)
      │
      ├── 특수 키 변환 (VT_MAP 테이블)
      │     Enter → \r
      │     Backspace → \x7f
      │     방향키 ↑ → \x1b[A
      │     PageUp → \x1b[5~
      │     F1 → \x1bOP   등
      │
      └── 일반 텍스트 → UTF-8 인코딩
            ▼
      [TerminalView._write(data: bytes)]
            │
            ├── [Windows + winpty] winpty.PTY.write(str)
            ├── [Windows + subprocess] stdin.write(bytes)
            ├── [Unix + ptyprocess] PtyProcess.write(str)
            └── [Unix + subprocess] stdin.write(bytes)
                  ▼
            [쉘 프로세스] (키 입력 처리)
```

---

## 3.4 데이터 흐름: 설정 변경

```
[사용자 설정 변경]
      │  Ctrl+, 또는 편집 메뉴 → 설정 클릭
      ▼
[SettingsDialog.exec()]
      │  각 페이지에서 값 수정
      │  Apply 버튼 클릭
      ▼
[AppSettings.save()]
      │  ~/.conemu-py/config.json 파일 갱신
      ▼
[_notify_settings_changed()]
      │  등록된 모든 콜백 호출
      ▼
[ConEmuApp._apply_settings()]
      │  창 제목, 크기, 탭 위치 등 갱신
      │  모든 TerminalView.apply_settings(s) 호출
      ▼
[TerminalView.apply_settings()]
      │  폰트 재계산, 셀 크기 갱신
      ▼
[TerminalView.update()]
      │  화면 다시 그리기
```

---

## 3.5 멀티 탭 구조

```
ConEmuApp
  └── QTabWidget
        ├── Tab 0: TerminalView  ──── PTY 프로세스 A (bash)
        │                        └── Reader Thread A
        ├── Tab 1: TerminalView  ──── PTY 프로세스 B (bash)
        │                        └── Reader Thread B
        └── Tab 2: TerminalView  ──── PTY 프로세스 C (bash)
                                  └── Reader Thread C
```

- 각 탭은 **완전히 독립적인** `TerminalView` 인스턴스를 가집니다.
- 각 `TerminalView`는 **독립적인 쉘 프로세스**와 **Reader 스레드**를 가집니다.
- 탭 전환 시 Qt가 현재 탭 위젯만 화면에 표시하며, 백그라운드 탭의 쉘은 계속 실행됩니다.

---

## 3.6 스레드 구조

```
Main Thread (Qt GUI)
  - Qt 이벤트 루프 실행
  - 모든 GUI 업데이트
  - 키보드/마우스 이벤트 처리
  - paintEvent 처리

PTY-Reader-Unix (또는 PTY-Reader-Win) Thread (탭마다 1개)
  - daemon=True (메인 스레드 종료 시 자동 종료)
  - PTY에서 데이터 읽기 (blocking)
  - pyte 스트림에 데이터 공급
  - process_exited 시그널 emit (GUI 스레드로 전달)
```

> **⚠️ 주의:** Reader 스레드는 직접 GUI를 수정하지 않습니다.  
> `process_exited` 시그널을 통해 Qt 메인 스레드에서 탭 제목을 갱신합니다.  
> Qt에서 GUI는 반드시 메인 스레드에서만 수정해야 합니다.

---

## 3.7 원본 ConEmu C++ 아키텍처와의 비교

원본 ConEmu는 **멀티 프로세스 + DLL 주입** 아키텍처를 사용합니다.  
ConEmu-Py는 이를 단순화하여 **단일 프로세스 + PTY** 아키텍처로 대체합니다.

| 구조 | 원본 ConEmu (C++) | ConEmu-Py (Python) |
|---|---|---|
| 메인 프로세스 | `ConEmu.exe` (GUI) | `python main.py` |
| 콘솔 서버 | `ConEmuCD.dll` (각 콘솔에 주입) | PTY (ptyprocess/pywinpty) |
| API 후킹 | `ConEmuHk.dll` (IAT 패치) | 미구현 (PTY로 대체) |
| 프로세스 통신 | Named Pipe (`\\.\pipe\ConEmu\*`) | PTY 파일 디스크립터 |
| 화면 버퍼 | `RealBuffer` (C++ 구조체) | `pyte.Screen` |
| ANSI 파서 | `ConAnsi` (C++ 클래스) | `pyte.ByteStream` |
| GUI 렌더링 | Win32 GDI / GDI+ | PyQt6 QPainter |
