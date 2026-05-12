"""
ConEmu Python 변환 - 터미널 뷰 위젯
CVirtualConsole + CVConChild 대응 (1단계 프로토타입)

- PySide6 QWidget 기반 커스텀 터미널 렌더링
- pyte를 사용한 VT100/ANSI 화면 버퍼 관리
- pywinpty(Windows) 또는 ptyprocess(Unix)로 PTY 관리
"""

import sys
import os
import threading
import traceback

print(f"[LOG][module] terminal_view 로딩 시작 — Python {sys.version}, 플랫폼={sys.platform}")

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, Signal, QRect
from PySide6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QKeyEvent,
    QMouseEvent, QPaintEvent, QResizeEvent, QClipboard
)

print("[LOG][module] PySide6 임포트 성공")

try:
    import pyte
    try:
        from importlib.metadata import version as _pkg_version
        _pyte_ver = _pkg_version("pyte")
    except Exception:
        _pyte_ver = "알 수 없음"
    print(f"[LOG][module] pyte 임포트 성공 — 버전={_pyte_ver}")
except ImportError:
    pyte = None  # type: ignore
    print("[ERROR][module] pyte 임포트 실패 — 'pip install pyte' 를 실행하세요")

print("[LOG][module] terminal_view 모듈 로딩 완료")

# ANSI 기본 16색 팔레트 (ConEmu 기본 팔레트 대응)
ANSI_COLORS = [
    "#000000",  # 0: Black
    "#800000",  # 1: Red (dark)
    "#008000",  # 2: Green (dark)
    "#808000",  # 3: Yellow (dark)
    "#000080",  # 4: Blue (dark)
    "#800080",  # 5: Magenta (dark)
    "#008080",  # 6: Cyan (dark)
    "#c0c0c0",  # 7: White (light gray)
    "#808080",  # 8: Bright Black (dark gray)
    "#ff0000",  # 9: Bright Red
    "#00ff00",  # 10: Bright Green
    "#ffff00",  # 11: Bright Yellow
    "#0000ff",  # 12: Bright Blue
    "#ff00ff",  # 13: Bright Magenta
    "#00ffff",  # 14: Bright Cyan
    "#ffffff",  # 15: Bright White
]

DEFAULT_FG = "#c0c0c0"
DEFAULT_BG = "#1e1e1e"


# pyte 색상명 → hex 매핑 (pyte는 색상을 이름 문자열로 반환)
PYTE_COLOR_NAMES = {
    "black":   "#000000",
    "red":     "#800000",
    "green":   "#008000",
    "brown":   "#808000",
    "blue":    "#000080",
    "magenta": "#800080",
    "cyan":    "#008080",
    "white":   "#c0c0c0",
}


def _resolve_color(color, default: str) -> QColor:
    """pyte 색상 값을 QColor로 변환"""
    if color == "default" or color is None:
        return QColor(default)
    # pyte가 반환하는 색상명 문자열 처리
    if isinstance(color, str):
        if color in PYTE_COLOR_NAMES:
            return QColor(PYTE_COLOR_NAMES[color])
        if color.startswith("#"):
            return QColor(color)
        print(f"[WARN][_resolve_color] 알 수 없는 색상명 문자열: {color!r} → default({default}) 사용")
    # 정수 인덱스 (256색 팔레트)
    if isinstance(color, int):
        if 0 <= color < len(ANSI_COLORS):
            return QColor(ANSI_COLORS[color])
        print(f"[WARN][_resolve_color] 팔레트 범위 벗어남: color={color} (팔레트 크기={len(ANSI_COLORS)})")
    return QColor(default)


class TerminalView(QWidget):
    """
    터미널 뷰 위젯.
    CVirtualConsole (C++) 대응.
    """

    title_changed = Signal(str)
    process_exited = Signal()

    # 우선순위 순으로 시도할 폰트 목록
    _FONT_CANDIDATES = [
        "Consolas",          # Windows
        "Cascadia Code",     # Windows Terminal 기본
        "DejaVu Sans Mono",  # Linux 광범위 지원
        "Liberation Mono",   # Linux RHEL/Fedora 계열
        "Courier New",       # 모든 OS
        "Monospace",         # Linux 제네릭 별칭
        "Courier",           # 최후 fallback
    ]

    @staticmethod
    def _pick_font(size: int) -> "QFont":
        """시스템에서 사용 가능한 모노스페이스 폰트를 찾아 반환"""
        print(f"[LOG][_pick_font] 폰트 탐색 시작 — 요청 크기={size}pt")
        from PySide6.QtGui import QFontDatabase
        available = set(QFontDatabase.families())
        print(f"[LOG][_pick_font] 시스템 폰트 패밀리 수={len(available)}")
        for name in TerminalView._FONT_CANDIDATES:
            if name in available:
                font = QFont(name, size)
                font.setFixedPitch(True)
                print(f"[LOG][_pick_font] 선택됨: '{name}' {size}pt")
                return font
            else:
                print(f"[LOG][_pick_font] 없음: '{name}'")
        # 하나도 없으면 Qt 기본 고정폭 폰트
        print("[WARN][_pick_font] 후보 폰트 전부 없음 → QFontDatabase.systemFont(FixedFont) 사용")
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(size)
        print(f"[LOG][_pick_font] 시스템 기본 고정폭 폰트: '{font.family()}' {font.pointSize()}pt")
        return font

    def _build_font_from_settings(self) -> "QFont":
        """AppSettings의 폰트 설정으로 QFont 생성. 설정 없으면 시스템 자동 탐색."""
        s = self._settings
        if s is not None:
            family = s.font_family
            size   = s.font_size
            bold   = s.font_bold
            if family:
                font = QFont(family, size)
                font.setBold(bold)
                font.setFixedPitch(True)
                print(f"[LOG][_build_font_from_settings] 설정 폰트 사용: '{family}' {size}pt bold={bold}")
                return font
        return self._pick_font(12)

    def apply_settings(self, settings=None) -> None:
        """AppSettings 변경 시 폰트·색상 등을 재적용 (설정 다이얼로그 Apply 후 호출)"""
        if settings is not None:
            self._settings = settings
        self._font = self._build_font_from_settings()
        fm = QFontMetrics(self._font)
        self._cell_w = fm.horizontalAdvance("M")
        self._cell_h = fm.height()
        print(f"[LOG][apply_settings] 폰트 갱신: '{self._font.family()}' "
              f"{self._font.pointSize()}pt, 셀={self._cell_w}×{self._cell_h}px")
        self.update()   # 다시 그리기

    def __init__(self, parent=None):
        print(f"[LOG][__init__] TerminalView 생성 시작 — parent={parent!r}")
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setCursor(Qt.CursorShape.IBeamCursor)
        print("[LOG][__init__] 위젯 속성 설정 완료 (FocusPolicy=StrongFocus, WA_OpaquePaintEvent, IBeamCursor)")

        # 설정 로드 (AppSettings 싱글턴)
        try:
            from config.settings import AppSettings
            self._settings = AppSettings.instance()
        except Exception:
            self._settings = None

        # 폰트 초기화 (설정 우선, 없으면 시스템 탐색)
        self._font = self._build_font_from_settings()
        print(f"[LOG][__init__] 폰트 확정: '{self._font.family()}' {self._font.pointSize()}pt")
        fm = QFontMetrics(self._font)
        self._cell_w = fm.horizontalAdvance("M")
        self._cell_h = fm.height()
        print(f"[LOG][__init__] 셀 크기: {self._cell_w}w × {self._cell_h}h px "
              f"(ascent={fm.ascent()}, descent={fm.descent()})")

        # 화면 크기 (행/열)
        self._cols = 80
        self._rows = 24
        print(f"[LOG][__init__] 초기 화면 크기: {self._cols}열 × {self._rows}행")

        # pyte 화면 버퍼 (RealBuffer 대응)
        self._screen: "pyte.Screen | None" = None
        self._stream: "pyte.ByteStream | None" = None
        self._init_pyte()

        # PTY / 프로세스
        self._pty = None
        self._reader_thread: threading.Thread | None = None
        self._running = False
        print("[LOG][__init__] _pty=None, _running=False 초기화")

        # 화면 갱신 타이머
        self._repaint_timer = QTimer(self)
        self._repaint_timer.setInterval(16)  # ~60fps
        self._repaint_timer.timeout.connect(self.update)
        print("[LOG][__init__] repaint 타이머 생성 완료 (16ms 간격, 아직 미시작)")

        # 렌더링 카운터 초기화
        self._paint_count = 0
        print("[LOG][__init__] TerminalView 생성 완료")

    # ------------------------------------------------------------------
    # pyte 화면 버퍼 초기화
    # ------------------------------------------------------------------

    def _init_pyte(self):
        print(f"[LOG][_init_pyte] 호출 — pyte 사용 가능={pyte is not None}, "
              f"크기=({self._cols}열 × {self._rows}행)")
        if pyte is None:
            print("[ERROR][_init_pyte] pyte가 없어서 버퍼를 초기화할 수 없습니다.")
            return
        self._screen = pyte.Screen(self._cols, self._rows)
        self._stream = pyte.ByteStream(self._screen)
        print(f"[LOG][_init_pyte] 화면 버퍼 생성 완료 — "
              f"Screen({self._screen.columns}열 × {self._screen.lines}행), "
              f"ByteStream 연결됨")

    # ------------------------------------------------------------------
    # PTY 시작/중지
    # ------------------------------------------------------------------

    def start(self):
        """터미널 프로세스 시작 (CRealConsole::Start() 대응)"""
        print(f"[LOG][start] 호출 — 플랫폼={sys.platform}, _running={self._running}, _pty={self._pty!r}")
        if sys.platform == "win32":
            print("[LOG][start] Windows 경로 선택")
            self._start_windows()
        else:
            print("[LOG][start] Unix 경로 선택")
            self._start_unix()
        self._running = True
        self._repaint_timer.start()
        print(f"[LOG][start] 완료 — _running=True, repaint 타이머 시작, _pty={self._pty!r}, "
              f"_reader_thread={self._reader_thread!r}")

    def _start_windows(self):
        """Windows PTY (pywinpty)"""
        print("[LOG][_start_windows] 호출")
        try:
            import winpty  # pywinpty
            print(f"[LOG][_start_windows] pywinpty 임포트 성공 — 버전 확인 시도")
            try:
                from importlib.metadata import version as _v
                print(f"[LOG][_start_windows] winpty 버전={_v('pywinpty')}")
            except Exception:
                print("[LOG][_start_windows] winpty 버전 확인 불가")
            self._pty = winpty.PTY(self._cols, self._rows)
            print(f"[LOG][_start_windows] PTY 객체 생성 — 크기=({self._cols}×{self._rows})")
            shell = os.environ.get("COMSPEC", "cmd.exe")
            print(f"[LOG][_start_windows] 쉘 경로: {shell}")
            self._pty.spawn(shell)
            print("[LOG][_start_windows] PTY spawn 완료")
        except ImportError as ie:
            print(f"[WARN][_start_windows] pywinpty ImportError: {ie} → subprocess fallback 사용")
            import subprocess
            shell = os.environ.get("COMSPEC", "cmd.exe")
            print(f"[LOG][_start_windows] subprocess 쉘: {shell}")
            self._pty = subprocess.Popen(
                [shell],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            print(f"[LOG][_start_windows] subprocess 시작 — PID={self._pty.pid}")
        except Exception as e:
            print(f"[ERROR][_start_windows] PTY 시작 실패: {type(e).__name__}: {e}")
            traceback.print_exc()
            return
        self._reader_thread = threading.Thread(
            target=self._read_loop_windows, daemon=True, name="PTY-Reader-Win"
        )
        self._reader_thread.start()
        print(f"[LOG][_start_windows] 읽기 스레드 시작됨 — {self._reader_thread.name}")

    def _start_unix(self):
        """Unix PTY (ptyprocess)"""
        print("[LOG][_start_unix] 호출")
        try:
            import ptyprocess
            print("[LOG][_start_unix] ptyprocess 임포트 성공")
            try:
                from importlib.metadata import version as _v
                print(f"[LOG][_start_unix] ptyprocess 버전={_v('ptyprocess')}")
            except Exception:
                print("[LOG][_start_unix] ptyprocess 버전 확인 불가")
            shell = os.environ.get("SHELL", "/bin/bash")
            print(f"[LOG][_start_unix] 쉘 경로: {shell}")
            self._pty = ptyprocess.PtyProcess.spawn([shell])
            print(f"[LOG][_start_unix] PTY spawn 완료 — PID={self._pty.pid}, "
                  f"fd={self._pty.fd}, closed={self._pty.closed}")
        except ImportError as ie:
            print(f"[WARN][_start_unix] ptyprocess ImportError: {ie} → subprocess fallback")
            print("[WARN][_start_unix] 'pip install ptyprocess' 설치를 권장합니다")
            import subprocess
            shell = os.environ.get("SHELL", "/bin/sh")
            print(f"[LOG][_start_unix] subprocess 쉘: {shell}")
            self._pty = subprocess.Popen(
                [shell],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            print(f"[LOG][_start_unix] subprocess 시작 — PID={self._pty.pid}")
        except Exception as e:
            print(f"[ERROR][_start_unix] PTY 시작 실패: {type(e).__name__}: {e}")
            traceback.print_exc()
            return
        self._reader_thread = threading.Thread(
            target=self._read_loop_unix, daemon=True, name="PTY-Reader-Unix"
        )
        self._reader_thread.start()
        print(f"[LOG][_start_unix] 읽기 스레드 시작됨 — {self._reader_thread.name}")

    def stop(self):
        """터미널 프로세스 종료"""
        print(f"[LOG][stop] 호출 — _running={self._running}, _pty={self._pty!r}")
        self._running = False
        self._repaint_timer.stop()
        print("[LOG][stop] repaint 타이머 중지")
        if self._pty is not None:
            try:
                if sys.platform == "win32":
                    print("[LOG][stop] Windows: _pty.close() 호출")
                    self._pty.close()
                else:
                    print("[LOG][stop] Unix: _pty.terminate() 호출")
                    self._pty.terminate()
                print("[LOG][stop] PTY 종료 완료")
            except Exception as e:
                print(f"[WARN][stop] PTY 종료 중 오류: {type(e).__name__}: {e}")
        else:
            print("[LOG][stop] _pty가 None이므로 종료 건너뜀")
        print("[LOG][stop] 완료")

    # ------------------------------------------------------------------
    # PTY 읽기 루프
    # ------------------------------------------------------------------

    def _read_loop_windows(self):
        """Windows PTY 출력 읽기 루프 (ConEmuSrv 역할)"""
        print("[LOG][_read_loop_windows] 읽기 루프 시작")
        import winpty
        is_winpty = isinstance(self._pty, winpty.PTY)
        print(f"[LOG][_read_loop_windows] PTY 타입: {'winpty.PTY' if is_winpty else 'subprocess.Popen'}")
        read_count = 0
        while self._running:
            try:
                if is_winpty:
                    # winpty.PTY.read()의 첫 번째 파라미터는 blocking(bool)임.
                    # read(4096) 처럼 int를 positional로 넘기면
                    # "int object cannot be cast as bool" TypeError 발생 → keyword 사용.
                    data = self._pty.read(blocking=False)
                    if data:
                        read_count += 1
                        if read_count <= 10 or read_count % 100 == 0:
                            print(f"[LOG][_read_loop_windows] 수신 #{read_count}: {len(data)}바이트 "
                                  f"(앞20={data[:20]!r})")
                        self._feed(data.encode("utf-8", errors="replace"))
                else:
                    # subprocess fallback
                    data = self._pty.stdout.read(4096)
                    if not data:
                        print("[LOG][_read_loop_windows] subprocess stdout EOF → 루프 종료")
                        break
                    read_count += 1
                    if read_count <= 10 or read_count % 100 == 0:
                        print(f"[LOG][_read_loop_windows] subprocess 수신 #{read_count}: "
                              f"{len(data)}바이트 (앞20={data[:20]!r})")
                    self._feed(data)
            except Exception as e:
                print(f"[ERROR][_read_loop_windows] 읽기 오류: {type(e).__name__}: {e}")
                traceback.print_exc()
                break
        print(f"[LOG][_read_loop_windows] 루프 종료 — 총 {read_count}회 읽음")
        self.process_exited.emit()

    def _read_loop_unix(self):
        """Unix PTY 출력 읽기 루프"""
        import subprocess
        is_subprocess = isinstance(self._pty, subprocess.Popen)
        print(f"[LOG][_read_loop_unix] 루프 시작 — "
              f"PTY 타입={'subprocess.Popen' if is_subprocess else type(self._pty).__name__}")
        read_count = 0
        while self._running:
            try:
                if is_subprocess:
                    data = self._pty.stdout.read(4096)
                else:
                    data = self._pty.read(4096)
                if not data:
                    print("[LOG][_read_loop_unix] EOF 수신 → 루프 종료")
                    break
                read_count += 1
                if read_count <= 10 or read_count % 100 == 0:
                    print(f"[LOG][_read_loop_unix] 수신 #{read_count}: {len(data)}바이트 "
                          f"type={type(data).__name__} (앞30={data[:30]!r})")
                self._feed(data if isinstance(data, bytes) else data.encode())
            except OSError as e:
                print(f"[ERROR][_read_loop_unix] OSError (PTY 닫힘 가능성): {e.errno} {e.strerror}")
                break
            except Exception as e:
                print(f"[ERROR][_read_loop_unix] 읽기 오류: {type(e).__name__}: {e}")
                traceback.print_exc()
                break
        print(f"[LOG][_read_loop_unix] 루프 종료 — 총 {read_count}회 읽음")
        self.process_exited.emit()

    def _feed(self, data: bytes):
        """PTY 출력을 pyte 스트림에 공급 (ConAnsi 역할)"""
        if self._stream is None:
            print(f"[WARN][_feed] _stream이 None — {len(data)}바이트 버림")
            return
        try:
            self._stream.feed(data)
        except Exception as e:
            print(f"[ERROR][_feed] pyte stream.feed 실패: {type(e).__name__}: {e}")
            traceback.print_exc()
            return
        # 타이틀 변경 감지
        if self._screen and self._screen.title:
            print(f"[LOG][_feed] 타이틀 변경 감지: {self._screen.title!r}")
            self.title_changed.emit(self._screen.title)

    # ------------------------------------------------------------------
    # 렌더링 (CVirtualConsole::Paint() 대응)
    # ------------------------------------------------------------------

    def paintEvent(self, event: QPaintEvent):
        self._paint_count += 1
        painter = QPainter(self)
        painter.setFont(self._font)

        # 설정에서 기본 색상 가져오기
        s = self._settings
        cfg_fg = s.default_fg if s else DEFAULT_FG
        cfg_bg = s.default_bg if s else DEFAULT_BG

        # 전체 배경 채우기
        painter.fillRect(self.rect(), QColor(cfg_bg))

        if self._screen is None:
            painter.setPen(QColor(cfg_fg))
            painter.drawText(10, 20, "pyte 라이브러리가 필요합니다: pip install pyte")
            if self._paint_count <= 3:
                print(f"[LOG][paintEvent] #{self._paint_count}: _screen=None, 안내 문구 표시")
            return

        fm = QFontMetrics(self._font)
        rendered_chars = 0
        widget_w = self.width()
        widget_h = self.height()

        if self._paint_count <= 3:
            print(f"[LOG][paintEvent] #{self._paint_count}: "
                  f"위젯크기={widget_w}×{widget_h}px, "
                  f"셀크기={self._cell_w}×{self._cell_h}px, "
                  f"화면버퍼={self._screen.columns}×{self._screen.lines}, "
                  f"_running={self._running}")

        for row_idx in range(self._screen.lines):
            for col_idx in range(self._screen.columns):
                char = self._screen.buffer[row_idx][col_idx]

                fg = _resolve_color(char.fg, cfg_fg)
                bg = _resolve_color(char.bg, cfg_bg)

                x = col_idx * self._cell_w
                y = row_idx * self._cell_h

                # 배경 그리기
                if char.bg != "default":
                    painter.fillRect(x, y, self._cell_w, self._cell_h, bg)

                # 텍스트 그리기
                ch = char.data
                if ch and ch != " ":
                    painter.setPen(fg)
                    painter.drawText(x, y + fm.ascent(), ch)
                    rendered_chars += 1

        if self._paint_count <= 3 or (rendered_chars > 0 and self._paint_count % 60 == 0):
            print(f"[LOG][paintEvent] #{self._paint_count}: 렌더된 문자={rendered_chars}개")

        # 커서 그리기
        if self._screen.cursor:
            cx = self._screen.cursor.x * self._cell_w
            cy = self._screen.cursor.y * self._cell_h
            cursor_style = s.cursor_style if s else "block"
            if cursor_style == "block":
                painter.fillRect(cx, cy, self._cell_w, self._cell_h, QColor("#ffffff"))
                char = self._screen.buffer[self._screen.cursor.y][self._screen.cursor.x]
                if char.data and char.data != " ":
                    painter.setPen(QColor(cfg_bg))
                    painter.drawText(cx, cy + fm.ascent(), char.data)
            elif cursor_style == "underline":
                painter.fillRect(cx, cy + self._cell_h - 2, self._cell_w, 2,
                                 QColor("#ffffff"))
            else:  # bar
                painter.fillRect(cx, cy, 2, self._cell_h, QColor("#ffffff"))

    # ------------------------------------------------------------------
    # 키보드 입력 처리 (CRealConsole::ProcessKeyDown() 대응)
    # ------------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        text = event.text()
        mods = event.modifiers()
        # PySide6에서 Qt enum은 int() 직접 변환 불가 → .value 사용 (PyQt5 호환)
        key_int = key.value if hasattr(key, 'value') else int(key)
        mods_int = mods.value if hasattr(mods, 'value') else int(mods)
        print(f"[LOG][keyPressEvent] key={key}({hex(key_int)}), text={text!r}, "
              f"mods={mods_int:#010x}, _pty={self._pty!r}, _running={self._running}")

        if self._pty is None:
            print("[WARN][keyPressEvent] _pty가 None — 키 입력 무시 (프로세스 없음)")
            return

        # 특수 키 변환 테이블 (VK_* → VT 시퀀스)
        VT_MAP = {
            Qt.Key.Key_Return:    b"\r",
            Qt.Key.Key_Enter:     b"\r",
            Qt.Key.Key_Backspace: b"\x7f",
            Qt.Key.Key_Tab:       b"\t",
            Qt.Key.Key_Escape:    b"\x1b",
            Qt.Key.Key_Up:        b"\x1b[A",
            Qt.Key.Key_Down:      b"\x1b[B",
            Qt.Key.Key_Right:     b"\x1b[C",
            Qt.Key.Key_Left:      b"\x1b[D",
            Qt.Key.Key_Home:      b"\x1b[H",
            Qt.Key.Key_End:       b"\x1b[F",
            Qt.Key.Key_PageUp:    b"\x1b[5~",
            Qt.Key.Key_PageDown:  b"\x1b[6~",
            Qt.Key.Key_Delete:    b"\x1b[3~",
            Qt.Key.Key_Insert:    b"\x1b[2~",
            Qt.Key.Key_F1:        b"\x1bOP",
            Qt.Key.Key_F2:        b"\x1bOQ",
            Qt.Key.Key_F3:        b"\x1bOR",
            Qt.Key.Key_F4:        b"\x1bOS",
        }

        # Ctrl+C (클립보드 복사와 구분하여 처리)
        if mods & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_C and not self._has_selection():
                print("[LOG][keyPressEvent] Ctrl+C → ETX(\\x03) 전송")
                self._write(b"\x03")
                return
            if key == Qt.Key.Key_D:
                print("[LOG][keyPressEvent] Ctrl+D → EOT(\\x04) 전송")
                self._write(b"\x04")
                return
            if key == Qt.Key.Key_L:
                print("[LOG][keyPressEvent] Ctrl+L → FF(\\x0c) 전송")
                self._write(b"\x0c")
                return
            if key == Qt.Key.Key_Z:
                print("[LOG][keyPressEvent] Ctrl+Z → SUB(\\x1a) 전송")
                self._write(b"\x1a")
                return

        data = VT_MAP.get(key)
        if data:
            print(f"[LOG][keyPressEvent] 특수 키 → VT 시퀀스 {data!r} 전송")
            self._write(data)
        elif text:
            encoded = text.encode("utf-8")
            print(f"[LOG][keyPressEvent] 텍스트 전송: {text!r} → bytes={encoded!r}")
            self._write(encoded)
        else:
            print(f"[LOG][keyPressEvent] 매핑 없는 키 무시 (key={key})")

    def _has_selection(self) -> bool:
        # TODO: 2단계 이후 선택 영역 구현
        print("[LOG][_has_selection] 호출 → False (미구현)")
        return False

    def _write(self, data: bytes):
        """PTY에 데이터 쓰기"""
        print(f"[LOG][_write] 호출 — data={data!r} ({len(data)}바이트), "
              f"_pty={self._pty!r}, platform={sys.platform}")
        if self._pty is None:
            print("[WARN][_write] _pty가 None이라 쓰기 불가")
            return
        try:
            import subprocess
            if sys.platform == "win32":
                import winpty
                if isinstance(self._pty, winpty.PTY):
                    text = data.decode("utf-8", errors="replace")
                    print(f"[LOG][_write] winpty.PTY.write(str) — '{text!r}'")
                    self._pty.write(text)
                else:
                    print(f"[LOG][_write] subprocess.stdin.write(bytes) — {data!r}")
                    self._pty.stdin.write(data)
                    self._pty.stdin.flush()
            else:
                if isinstance(self._pty, subprocess.Popen):
                    print(f"[LOG][_write] subprocess.stdin.write(bytes) — {data!r}")
                    self._pty.stdin.write(data)
                    self._pty.stdin.flush()
                else:
                    text = data.decode("utf-8", errors="replace")
                    print(f"[LOG][_write] ptyprocess.write(str) — '{text!r}'")
                    self._pty.write(text)
            print("[LOG][_write] 쓰기 성공")
        except Exception as e:
            print(f"[ERROR][_write] 쓰기 실패: {type(e).__name__}: {e}")
            traceback.print_exc()

    # ------------------------------------------------------------------
    # 창 크기 변경 처리
    # ------------------------------------------------------------------

    def resizeEvent(self, event: QResizeEvent):
        old_size = event.oldSize()
        new_size = event.size()
        print(f"[LOG][resizeEvent] 호출 — 이전={old_size.width()}×{old_size.height()}px, "
              f"신규={new_size.width()}×{new_size.height()}px")
        super().resizeEvent(event)
        w = max(1, new_size.width() // self._cell_w)
        h = max(1, new_size.height() // self._cell_h)
        print(f"[LOG][resizeEvent] 픽셀→셀 변환: {w}열 × {h}행 (현재: {self._cols}×{self._rows})")
        if w != self._cols or h != self._rows:
            print(f"[LOG][resizeEvent] 화면 버퍼/PTY 크기 갱신: {self._cols}×{self._rows} → {w}×{h}")
            self._cols = w
            self._rows = h
            self._resize_pty(w, h)
            if self._screen is not None:
                self._screen.resize(h, w)
                print(f"[LOG][resizeEvent] pyte Screen.resize({h}, {w}) 완료")
        else:
            print("[LOG][resizeEvent] 열/행 수 변화 없음 — 크기 갱신 생략")

    def _resize_pty(self, cols: int, rows: int):
        """PTY 크기 갱신"""
        print(f"[LOG][_resize_pty] 호출 — {cols}열 × {rows}행, _pty={self._pty!r}")
        if self._pty is None:
            print("[LOG][_resize_pty] _pty가 None — 크기 갱신 생략")
            return
        try:
            if sys.platform == "win32":
                import winpty
                if isinstance(self._pty, winpty.PTY):
                    self._pty.set_size(cols, rows)
                    print(f"[LOG][_resize_pty] winpty.set_size({cols}, {rows}) 성공")
                else:
                    print("[LOG][_resize_pty] Windows subprocess fallback — PTY 크기 변경 불가")
            else:
                import subprocess
                if isinstance(self._pty, subprocess.Popen):
                    print("[LOG][_resize_pty] subprocess fallback — PTY 크기 변경 불가")
                else:
                    self._pty.setwinsize(rows, cols)
                    print(f"[LOG][_resize_pty] ptyprocess.setwinsize({rows}, {cols}) 성공")
        except Exception as e:
            print(f"[WARN][_resize_pty] 크기 변경 실패: {type(e).__name__}: {e}")

    # ------------------------------------------------------------------
    # 마우스 (기본 - 3단계에서 확장)
    # ------------------------------------------------------------------

    def sizeHint(self):
        from PySide6.QtCore import QSize
        hint = QSize(self._cols * self._cell_w, self._rows * self._cell_h)
        print(f"[LOG][sizeHint] → {hint.width()}×{hint.height()}px "
              f"({self._cols}열×{self._rows}행, 셀={self._cell_w}×{self._cell_h}px)")
        return hint

    def mousePressEvent(self, event: QMouseEvent):
        btn = event.button()
        pos = event.position()
        print(f"[LOG][mousePressEvent] 클릭: button={btn}, pos=({pos.x():.0f},{pos.y():.0f})")
        self.setFocus()
        print("[LOG][mousePressEvent] setFocus() 완료")
