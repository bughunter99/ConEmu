"""
ConEmu Python 변환 - 설정 관리 (SettingsStorage 대응)

원본 C++ 클래스:
  SettingsStorage  → AppSettings (저장 백엔드)
  CSetPgGeneral    → general 섹션
  CSetPgFonts      → fonts 섹션
  CSetPgColors     → colors 섹션
  CSetPgTabs       → tabs 섹션
  CSetPgKeyboard   → keyboard 섹션
  CSetPgCursor     → cursor 섹션

설정 파일 위치: ~/.conemu-py/config.json
"""

import json
import os
import sys
from typing import Any

# 기본 설정 파일 경로
_CONFIG_DIR  = os.path.join(os.path.expanduser("~"), ".conemu-py")
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "config.json")

# 기본값 정의 (원본 ConEmu 기본값에 맞춤)
_DEFAULTS: dict[str, Any] = {
    # ── General (CSetPgGeneral) ──────────────────────────────────────────
    "general": {
        "startup_shell":     "",          # 빈 문자열 → OS 기본 셸
        "msys64_root":       "",          # MSYS2 설치 루트 (예: C:\msys64)
        "scrollback_lines":  9999,        # 스크롤백 버퍼 줄 수
        "save_on_exit":      True,        # 종료 시 설정 저장
        "config_file":       _CONFIG_FILE,
    },
    # ── Fonts (CSetPgFonts) ─────────────────────────────────────────────
    "fonts": {
        "family":      "Consolas" if sys.platform == "win32" else "Monospace",
        "size":        12,
        "bold":        False,
        "antialiasing": True,
    },
    # ── Colors (CSetPgColors) ────────────────────────────────────────────
    "colors": {
        "default_fg": "#c0c0c0",
        "default_bg": "#1e1e1e",
        # 16-color ANSI 팔레트 (ConEmu 기본 팔레트)
        "palette": [
            "#000000",  # 0  Black
            "#800000",  # 1  Dark Red
            "#008000",  # 2  Dark Green
            "#808000",  # 3  Dark Yellow
            "#000080",  # 4  Dark Blue
            "#800080",  # 5  Dark Magenta
            "#008080",  # 6  Dark Cyan
            "#c0c0c0",  # 7  Light Gray
            "#808080",  # 8  Dark Gray
            "#ff0000",  # 9  Bright Red
            "#00ff00",  # 10 Bright Green
            "#ffff00",  # 11 Bright Yellow
            "#0000ff",  # 12 Bright Blue
            "#ff00ff",  # 13 Bright Magenta
            "#00ffff",  # 14 Bright Cyan
            "#ffffff",  # 15 White
        ],
    },
    # ── Appearance (CSetPgAppear) ────────────────────────────────────────
    "appearance": {
        "window_title":  "ConEmu-Py",
        "tab_position":  "top",   # "top" | "bottom"
        "tab_title_fmt": "%s",    # %s → 셸 타이틀
    },
    # ── Cursor (CSetPgCursor) ────────────────────────────────────────────
    "cursor": {
        "style": "block",   # "block" | "underline" | "bar"
        "blink": True,
    },
    # ── Keyboard shortcuts (CSetPgKeyboard) ──────────────────────────────
    "keyboard": {
        "new_tab":     "Ctrl+T",
        "close_tab":   "Ctrl+W",
        "settings":    "Ctrl+,",
        "copy":        "Ctrl+Shift+C",
        "paste":       "Ctrl+Shift+V",
        "find":        "Ctrl+F",
        "next_tab":    "Ctrl+Tab",
        "prev_tab":    "Ctrl+Shift+Tab",
    },
    # ── Window size/position (CSetPgSizePos) ────────────────────────────
    "window": {
        "width":  900,
        "height": 600,
        "x":      -1,   # -1 → OS 기본 위치
        "y":      -1,
        "maximized": False,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """override를 base에 재귀적으로 병합 (누락된 키는 base 값 유지)"""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


class AppSettings:
    """
    애플리케이션 설정 관리자.
    C++ SettingsStorage / CESettings 대응.

    사용 예::

        s = AppSettings.instance()
        print(s.font_family)
        s.font_size = 14
        s.save()
    """

    _instance: "AppSettings | None" = None

    # ------------------------------------------------------------------
    # 싱글턴 접근자
    # ------------------------------------------------------------------

    @classmethod
    def instance(cls) -> "AppSettings":
        if cls._instance is None:
            cls._instance = AppSettings()
        return cls._instance

    # ------------------------------------------------------------------
    # 초기화
    # ------------------------------------------------------------------

    def __init__(self, config_file: str = _CONFIG_FILE):
        self._config_file = config_file
        self._data: dict[str, Any] = {}
        self.load()

    # ------------------------------------------------------------------
    # 저장 / 로드
    # ------------------------------------------------------------------

    def load(self) -> None:
        """JSON 파일에서 설정 로드. 파일이 없으면 기본값 사용."""
        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self._data = _deep_merge(_DEFAULTS, loaded)
            print(f"[LOG][AppSettings.load] '{self._config_file}' 로드 완료")
        except FileNotFoundError:
            self._data = _deep_merge(_DEFAULTS, {})
            print(f"[LOG][AppSettings.load] 파일 없음 — 기본값 사용: '{self._config_file}'")
        except Exception as e:
            self._data = _deep_merge(_DEFAULTS, {})
            print(f"[ERROR][AppSettings.load] 로드 실패: {e} — 기본값 사용")

    def save(self) -> None:
        """현재 설정을 JSON 파일로 저장."""
        try:
            os.makedirs(os.path.dirname(self._config_file), exist_ok=True)
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            print(f"[LOG][AppSettings.save] '{self._config_file}' 저장 완료")
        except Exception as e:
            print(f"[ERROR][AppSettings.save] 저장 실패: {e}")

    # ------------------------------------------------------------------
    # 저수준 접근자 (섹션 딕셔너리)
    # ------------------------------------------------------------------

    def get_section(self, section: str) -> dict:
        return self._data.setdefault(section, {})

    def _get(self, section: str, key: str) -> Any:
        return self.get_section(section).get(key)

    def _set(self, section: str, key: str, value: Any) -> None:
        self.get_section(section)[key] = value

    # ------------------------------------------------------------------
    # General 설정 프로퍼티
    # ------------------------------------------------------------------

    @property
    def startup_shell(self) -> str:
        return self._get("general", "startup_shell") or ""

    @startup_shell.setter
    def startup_shell(self, v: str) -> None:
        self._set("general", "startup_shell", v)

    @property
    def msys64_root(self) -> str:
        return self._get("general", "msys64_root") or ""

    @msys64_root.setter
    def msys64_root(self, v: str) -> None:
        self._set("general", "msys64_root", v)

    @property
    def scrollback_lines(self) -> int:
        return int(self._get("general", "scrollback_lines") or 9999)

    @scrollback_lines.setter
    def scrollback_lines(self, v: int) -> None:
        self._set("general", "scrollback_lines", max(100, int(v)))

    @property
    def save_on_exit(self) -> bool:
        return bool(self._get("general", "save_on_exit"))

    @save_on_exit.setter
    def save_on_exit(self, v: bool) -> None:
        self._set("general", "save_on_exit", bool(v))

    # ------------------------------------------------------------------
    # Fonts 설정 프로퍼티
    # ------------------------------------------------------------------

    @property
    def font_family(self) -> str:
        return self._get("fonts", "family") or _DEFAULTS["fonts"]["family"]

    @font_family.setter
    def font_family(self, v: str) -> None:
        self._set("fonts", "family", v)

    @property
    def font_size(self) -> int:
        return int(self._get("fonts", "size") or 12)

    @font_size.setter
    def font_size(self, v: int) -> None:
        self._set("fonts", "size", max(6, min(72, int(v))))

    @property
    def font_bold(self) -> bool:
        return bool(self._get("fonts", "bold"))

    @font_bold.setter
    def font_bold(self, v: bool) -> None:
        self._set("fonts", "bold", bool(v))

    # ------------------------------------------------------------------
    # Colors 설정 프로퍼티
    # ------------------------------------------------------------------

    @property
    def default_fg(self) -> str:
        return self._get("colors", "default_fg") or _DEFAULTS["colors"]["default_fg"]

    @default_fg.setter
    def default_fg(self, v: str) -> None:
        self._set("colors", "default_fg", v)

    @property
    def default_bg(self) -> str:
        return self._get("colors", "default_bg") or _DEFAULTS["colors"]["default_bg"]

    @default_bg.setter
    def default_bg(self, v: str) -> None:
        self._set("colors", "default_bg", v)

    @property
    def palette(self) -> list[str]:
        p = self._get("colors", "palette")
        if isinstance(p, list) and len(p) == 16:
            return p
        return list(_DEFAULTS["colors"]["palette"])

    @palette.setter
    def palette(self, v: list[str]) -> None:
        if len(v) == 16:
            self._set("colors", "palette", list(v))

    # ------------------------------------------------------------------
    # Appearance 설정 프로퍼티
    # ------------------------------------------------------------------

    @property
    def window_title(self) -> str:
        return self._get("appearance", "window_title") or "ConEmu-Py"

    @window_title.setter
    def window_title(self, v: str) -> None:
        self._set("appearance", "window_title", v)

    @property
    def tab_position(self) -> str:
        return self._get("appearance", "tab_position") or "top"

    @tab_position.setter
    def tab_position(self, v: str) -> None:
        self._set("appearance", "tab_position", v if v in ("top", "bottom") else "top")

    @property
    def tab_title_fmt(self) -> str:
        return self._get("appearance", "tab_title_fmt") or "%s"

    @tab_title_fmt.setter
    def tab_title_fmt(self, v: str) -> None:
        self._set("appearance", "tab_title_fmt", v)

    # ------------------------------------------------------------------
    # Cursor 설정 프로퍼티
    # ------------------------------------------------------------------

    @property
    def cursor_style(self) -> str:
        return self._get("cursor", "style") or "block"

    @cursor_style.setter
    def cursor_style(self, v: str) -> None:
        self._set("cursor", "style", v if v in ("block", "underline", "bar") else "block")

    @property
    def cursor_blink(self) -> bool:
        v = self._get("cursor", "blink")
        return True if v is None else bool(v)

    @cursor_blink.setter
    def cursor_blink(self, v: bool) -> None:
        self._set("cursor", "blink", bool(v))

    # ------------------------------------------------------------------
    # Keyboard 설정 프로퍼티
    # ------------------------------------------------------------------

    @property
    def shortcuts(self) -> dict[str, str]:
        return dict(self.get_section("keyboard"))

    def get_shortcut(self, action: str) -> str:
        return self.get_section("keyboard").get(action, "")

    def set_shortcut(self, action: str, key: str) -> None:
        self.get_section("keyboard")[action] = key

    # ------------------------------------------------------------------
    # Window 설정 프로퍼티
    # ------------------------------------------------------------------

    @property
    def window_width(self) -> int:
        return int(self._get("window", "width") or 900)

    @window_width.setter
    def window_width(self, v: int) -> None:
        self._set("window", "width", max(400, int(v)))

    @property
    def window_height(self) -> int:
        return int(self._get("window", "height") or 600)

    @window_height.setter
    def window_height(self, v: int) -> None:
        self._set("window", "height", max(300, int(v)))

    @property
    def window_x(self) -> int:
        return int(self._get("window", "x") or -1)

    @window_x.setter
    def window_x(self, v: int) -> None:
        self._set("window", "x", int(v))

    @property
    def window_y(self) -> int:
        return int(self._get("window", "y") or -1)

    @window_y.setter
    def window_y(self, v: int) -> None:
        self._set("window", "y", int(v))

    @property
    def window_maximized(self) -> bool:
        return bool(self._get("window", "maximized"))

    @window_maximized.setter
    def window_maximized(self, v: bool) -> None:
        self._set("window", "maximized", bool(v))
