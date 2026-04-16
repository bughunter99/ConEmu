# 5. 설정 가이드

ConEmu-Py의 모든 설정은 `~/.conemu-py/config.json` 파일에 저장됩니다.  
설정 파일이 없으면 기본값으로 자동 생성됩니다.

> **설정 파일 위치:**
> - Linux/macOS: `/home/사용자이름/.conemu-py/config.json`
> - Windows: `C:\Users\사용자이름\.conemu-py\config.json`

---

## 5.1 설정 다이얼로그 사용법

GUI로 설정을 변경하려면:

1. 메뉴 → **편집(E)** → **설정(S)…** 클릭  
   또는 단축키 **Ctrl+,** 입력

2. 좌측 목록에서 설정 페이지 선택

3. 원하는 값 변경

4. **Apply** 버튼으로 즉시 반영  
   **OK** 버튼으로 저장 후 닫기  
   **Cancel** 버튼으로 취소

---

## 5.2 전체 설정 파일 예시

```json
{
  "general": {
    "startup_shell": "",
    "scrollback_lines": 9999,
    "save_on_exit": true,
    "config_file": "/home/user/.conemu-py/config.json"
  },
  "fonts": {
    "family": "Consolas",
    "size": 12,
    "bold": false,
    "antialiasing": true
  },
  "colors": {
    "default_fg": "#c0c0c0",
    "default_bg": "#1e1e1e",
    "palette": [
      "#000000",
      "#800000",
      "#008000",
      "#808000",
      "#000080",
      "#800080",
      "#008080",
      "#c0c0c0",
      "#808080",
      "#ff0000",
      "#00ff00",
      "#ffff00",
      "#0000ff",
      "#ff00ff",
      "#00ffff",
      "#ffffff"
    ]
  },
  "appearance": {
    "window_title": "ConEmu-Py",
    "tab_position": "top",
    "tab_title_fmt": "%s"
  },
  "cursor": {
    "style": "block",
    "blink": true
  },
  "keyboard": {
    "new_tab":   "Ctrl+T",
    "close_tab": "Ctrl+W",
    "settings":  "Ctrl+,",
    "copy":      "Ctrl+Shift+C",
    "paste":     "Ctrl+Shift+V",
    "find":      "Ctrl+F",
    "next_tab":  "Ctrl+Tab",
    "prev_tab":  "Ctrl+Shift+Tab"
  },
  "window": {
    "width":     900,
    "height":    600,
    "x":         -1,
    "y":         -1,
    "maximized": false
  }
}
```

---

## 5.3 각 섹션 상세 설명

### `general` — 일반 설정

| 키 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `startup_shell` | string | `""` | 시작 시 실행할 쉘 경로. 비어 있으면 OS 기본 쉘 사용 (Linux: `$SHELL`, Windows: `%COMSPEC%`) |
| `scrollback_lines` | int | `9999` | 스크롤 히스토리 최대 줄 수. 100 이상이어야 합니다 |
| `save_on_exit` | bool | `true` | `true`이면 앱 종료 시 현재 설정을 자동으로 저장합니다 |

**예시 — zsh를 기본 쉘로 설정:**
```json
"general": {
  "startup_shell": "/bin/zsh"
}
```

---

### `fonts` — 폰트 설정

| 키 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `family` | string | `"Consolas"` (Win) / `"Monospace"` (Linux) | 폰트 패밀리 이름. 반드시 시스템에 설치된 고정폭(Monospace) 폰트여야 합니다 |
| `size` | int | `12` | 폰트 크기 (포인트). 6~72 범위 |
| `bold` | bool | `false` | `true`이면 굵은 글꼴 사용 |
| `antialiasing` | bool | `true` | 안티앨리어싱 여부 (현재는 Qt에 위임) |

**추천 폰트:**
- Windows: `Consolas`, `Cascadia Code`, `Cascadia Mono`
- Linux: `DejaVu Sans Mono`, `Liberation Mono`, `Ubuntu Mono`
- 맥: `Menlo`, `Monaco`, `SF Mono`

**예시 — 14pt Cascadia Code:**
```json
"fonts": {
  "family": "Cascadia Code",
  "size": 14,
  "bold": false
}
```

---

### `colors` — 색상 설정

| 키 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `default_fg` | string (hex) | `"#c0c0c0"` | 기본 전경색 (텍스트 색) |
| `default_bg` | string (hex) | `"#1e1e1e"` | 기본 배경색 |
| `palette` | array[16] | ConEmu 기본 팔레트 | ANSI 16색 팔레트 (순서 고정, 인덱스 0~15) |

**팔레트 인덱스 순서:**

| 인덱스 | 의미 | 기본값 |
|---|---|---|
| 0 | Black (검정) | `#000000` |
| 1 | Dark Red (어두운 빨강) | `#800000` |
| 2 | Dark Green (어두운 초록) | `#008000` |
| 3 | Dark Yellow (어두운 노랑) | `#808000` |
| 4 | Dark Blue (어두운 파랑) | `#000080` |
| 5 | Dark Magenta (어두운 자홍) | `#800080` |
| 6 | Dark Cyan (어두운 청록) | `#008080` |
| 7 | Light Gray (밝은 회색) | `#c0c0c0` |
| 8 | Dark Gray (어두운 회색) | `#808080` |
| 9 | Bright Red (밝은 빨강) | `#ff0000` |
| 10 | Bright Green (밝은 초록) | `#00ff00` |
| 11 | Bright Yellow (밝은 노랑) | `#ffff00` |
| 12 | Bright Blue (밝은 파랑) | `#0000ff` |
| 13 | Bright Magenta (밝은 자홍) | `#ff00ff` |
| 14 | Bright Cyan (밝은 청록) | `#00ffff` |
| 15 | White (흰색) | `#ffffff` |

**예시 — Solarized Dark 테마:**
```json
"colors": {
  "default_fg": "#839496",
  "default_bg": "#002b36",
  "palette": [
    "#073642", "#dc322f", "#859900", "#b58900",
    "#268bd2", "#d33682", "#2aa198", "#eee8d5",
    "#002b36", "#cb4b16", "#586e75", "#657b83",
    "#839496", "#6c71c4", "#93a1a1", "#fdf6e3"
  ]
}
```

---

### `appearance` — 외관 설정

| 키 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `window_title` | string | `"ConEmu-Py"` | 창 제목 표시줄 텍스트 |
| `tab_position` | string | `"top"` | 탭 위치. `"top"` 또는 `"bottom"` |
| `tab_title_fmt` | string | `"%s"` | 탭 타이틀 포맷. `%s` 자리에 쉘 타이틀이 들어갑니다 |

---

### `cursor` — 커서 설정

| 키 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `style` | string | `"block"` | 커서 모양. `"block"` (블록), `"underline"` (밑줄), `"bar"` (세로 막대) |
| `blink` | bool | `true` | 커서 깜빡임 여부 (현재 깜빡임 애니메이션은 미구현) |

커서 스타일 비교:

| 스타일 | 외관 | 설명 |
|---|---|---|
| `block` | `█` | 문자 전체를 덮는 흰색 박스 |
| `underline` | `_` | 문자 아래에 2px 흰색 줄 |
| `bar` | `\|` | 문자 왼쪽에 2px 흰색 수직선 |

---

### `keyboard` — 단축키 설정

단축키를 변경하려면 설정 파일의 `keyboard` 섹션을 수정하거나  
설정 다이얼로그의 **Keyboard** 페이지에서 편집합니다.

| 키 | 기본값 | 동작 |
|---|---|---|
| `new_tab` | `Ctrl+T` | 새 터미널 탭 열기 |
| `close_tab` | `Ctrl+W` | 현재 탭 닫기 |
| `settings` | `Ctrl+,` | 설정 다이얼로그 열기 |
| `copy` | `Ctrl+Shift+C` | 선택 텍스트 클립보드 복사 (미구현) |
| `paste` | `Ctrl+Shift+V` | 클립보드 붙여넣기 (미구현) |
| `find` | `Ctrl+F` | 터미널 내 텍스트 검색 (미구현) |
| `next_tab` | `Ctrl+Tab` | 다음 탭으로 전환 |
| `prev_tab` | `Ctrl+Shift+Tab` | 이전 탭으로 전환 |

---

### `window` — 창 크기/위치

앱 실행 중 창을 이동하거나 크기를 변경하면, 종료 시 자동으로 이 값이 갱신됩니다 (`save_on_exit: true`인 경우).

| 키 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `width` | int | `900` | 창 가로 크기 (px). 최소 400 |
| `height` | int | `600` | 창 세로 크기 (px). 최소 300 |
| `x` | int | `-1` | 창 왼쪽 상단 X 좌표. `-1`이면 OS 기본 위치 |
| `y` | int | `-1` | 창 왼쪽 상단 Y 좌표. `-1`이면 OS 기본 위치 |
| `maximized` | bool | `false` | `true`이면 최대화된 상태로 시작 |

---

## 5.4 설정 초기화 방법

설정을 초기화하려면 설정 파일을 삭제하면 됩니다:

```bash
# Linux/macOS
rm ~/.conemu-py/config.json

# Windows (명령 프롬프트)
del %USERPROFILE%\.conemu-py\config.json
```

다음 실행 시 기본값으로 새 설정 파일이 생성됩니다.

---

## 5.5 설정 파일 수동 편집 시 주의사항

- JSON 형식이어야 합니다. 잘못된 JSON이면 기본값으로 초기화됩니다.
- `palette` 배열은 반드시 **정확히 16개** 항목이어야 합니다.
- 색상 값은 반드시 `#RRGGBB` 형식이어야 합니다 (예: `#ff0000`).
- `font_size`는 6~72 범위 (범위 밖이면 자동으로 클리핑).
- `scrollback_lines`는 100 이상이어야 합니다.
