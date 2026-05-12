# ConEmu Python 변환 프로젝트

이 폴더는 ConEmu 터미널 에뮬레이터를 Python으로 변환하기 위한 분석 문서 및 소스코드를 포함합니다.

---

## 📂 폴더 구조

```
pyversion/
├── README.md              ← 이 파일
├── class_structure.md     ← 내부 클래스 구조 명세
├── data_flow.md           ← 데이터 흐름 명세
├── libraries.md           ← 사용 라이브러리 명세 및 Python 대응표
└── conversion_plan.md     ← 5단계 변환 계획
```

---

## 📋 분석 문서 요약

### [class_structure.md](./class_structure.md)
- ConEmu의 멀티 프로세스 모듈 구성 (ConEmu.exe, ConEmuCD.dll, ConEmuHk.dll 등)
- 핵심 클래스 계층도 (`CConEmuMain`, `CVirtualConsole`, `CRealConsole` 등)
- 각 클래스의 주요 멤버 변수 및 메서드
- 후킹 DLL 구조 분석

### [data_flow.md](./data_flow.md)
- 전체 아키텍처 다이어그램 (GUI ↔ ConEmuCD ↔ ConEmuHk ↔ 쉘 프로세스)
- 프로세스 시작 흐름
- 콘솔 출력/입력 데이터 흐름
- IPC 패킷 구조 (Named Pipe, 공유 메모리)
- 렌더링 파이프라인
- 설정 로드/저장 흐름

### [libraries.md](./libraries.md)
- Win32 API 사용 목록 및 Python 대응 라이브러리
- 시스템 DLL/COM 사용 목록
- C++ 커스텀 컨테이너 → Python 표준 타입 매핑
- 추천 Python 라이브러리 스택 (`PySide6`, `pyte`, `psutil`, `pywinpty`)
- `requirements.txt` 예상 내용

### [conversion_plan.md](./conversion_plan.md)
- **1단계**: 환경 설정 및 프로토타입 (빈 창 + 쉘 실행)
- **2단계**: 터미널 에뮬레이터 코어 (버퍼 파싱 + ANSI)
- **3단계**: GUI 렌더링 (커스텀 페인팅)
- **4단계**: 탭 / UI 완성 (멀티탭, 분할 창)
- **5단계**: 설정 / 고급 기능 / 테스트

---

## 🚀 빠른 시작 (1단계 시작 방법)

```bash
cd pyversion

# 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install PySide6 pyte psutil

# Windows 추가
pip install pywinpty pywin32

# 실행
python main.py
```

---

## ⚠️ 변환 범위 제한 사항

다음 기능들은 Python 변환 범위에서 **제외**됩니다:
- DLL 주입 + Windows API 후킹 (`ConEmuHk.dll`)
- 콘솔 프로세스 내 서버 데몬 (`ConEmuCD.dll`) → PTY로 대체
- FAR Manager 플러그인 연동
- DWM 투명/블러 효과 (고급 Aero 기능)
