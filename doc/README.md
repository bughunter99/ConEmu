# ConEmu-Py 문서 목차

> **ConEmu-Py**는 Windows 전용 터미널 에뮬레이터 [ConEmu](https://conemu.github.io)를  
> Python(PyQt6)으로 재구현한 크로스 플랫폼 프로젝트입니다.

---

## 문서 목록

| 파일 | 내용 |
|---|---|
| [01_overview.md](01_overview.md) | 프로젝트 개요, 목표, 원본 ConEmu와의 관계 |
| [02_installation.md](02_installation.md) | 설치 방법, 의존성, 실행 방법 |
| [03_architecture.md](03_architecture.md) | 전체 아키텍처, 컴포넌트 구조, 데이터 흐름 |
| [04_modules.md](04_modules.md) | 각 Python 모듈 상세 설명 |
| [05_configuration.md](05_configuration.md) | 설정 파일 가이드 (`~/.conemu-py/config.json`) |
| [06_shortcuts.md](06_shortcuts.md) | 단축키 목록 및 마우스 조작 방법 |
| [07_developer.md](07_developer.md) | 개발자 가이드 (기여, 테스트, 확장 방법) |
| [08_faq.md](08_faq.md) | 자주 묻는 질문 및 트러블슈팅 |

---

## 프로젝트 한눈에 보기

```
ConEmu-Py
├── pyversion/              ← Python 구현 루트
│   ├── main.py             ← 진입점 (python main.py 로 실행)
│   ├── app.py              ← 메인 애플리케이션 창 (ConEmuApp)
│   ├── requirements.txt    ← 의존 라이브러리 목록
│   ├── gui/                ← GUI 위젯
│   │   ├── terminal_view.py    ← 터미널 렌더링 위젯
│   │   └── settings_dialog.py  ← 설정 다이얼로그
│   ├── config/             ← 설정 관리
│   │   └── settings.py         ← AppSettings 싱글턴
│   ├── terminal/           ← 터미널 에뮬레이션 (확장 예정)
│   ├── ipc/                ← 프로세스 간 통신 (확장 예정)
│   └── tests/              ← 단위 테스트
│       └── test_terminal_buffer.py
└── doc/                    ← 이 문서 폴더
```

---

## 빠른 시작

```bash
# 1. 의존성 설치
cd pyversion
pip install -r requirements.txt

# 2. 실행
python main.py
```

자세한 내용은 [설치 가이드](02_installation.md)를 참조하세요.
