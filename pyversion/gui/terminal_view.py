"""
ConEmu Python 변환 - 터미널 뷰 위젯
CVirtualConsole + CVConChild 대응 (1단계 프로토타입)

- PyQt6 QWidget 기반 커스텀 터미널 렌더링
- pyte를 사용한 VT100/ANSI 화면 버퍼 관리
- pywinpty(Windows) 또는 ptyprocess(Unix)로 PTY 관리
"""

import sys
import os
import threading

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QKeyEvent,
    QMouseEvent, QPaintEvent, QResizeEvent, QClipboard
)

try:
    import pyte
except ImportError:
    pyte = None  # type: ignore

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
    # 정수 인덱스 (256색 팔레트)
    if isinstance(color, int) and 0 <= color < len(ANSI_COLORS):
        return QColor(ANSI_COLORS[color])
    return QColor(default)


class TerminalView(QWidget):
    """
    터미널 뷰 위젯.
    CVirtualConsole (C++) 대응.
    """

    title_changed = pyqtSignal(str)
    process_exited = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setCursor(Qt.CursorShape.IBeamCursor)

        # 폰트 (CFontMgr 대응)
        self._font = QFont("Consolas", 11)
        self._font.setFixedPitch(True)
        fm = QFontMetrics(self._font)
        self._cell_w = fm.horizontalAdvance("M")
        self._cell_h = fm.height()

        # 화면 크기 (행/열)
        self._cols = 80
        self._rows = 24

        # pyte 화면 버퍼 (RealBuffer 대응)
        self._screen: "pyte.Screen | None" = None
        self._stream: "pyte.ByteStream | None" = None
        self._init_pyte()

        # PTY / 프로세스
        self._pty = None
        self._reader_thread: threading.Thread | None = None
        self._running = False

        # 화면 갱신 타이머
        self._repaint_timer = QTimer(self)
        self._repaint_timer.setInterval(16)  # ~60fps
        self._repaint_timer.timeout.connect(self.update)

    # ------------------------------------------------------------------
    # pyte 화면 버퍼 초기화
    # ------------------------------------------------------------------

    def _init_pyte(self):
        if pyte is None:
            return
        self._screen = pyte.Screen(self._cols, self._rows)
        self._stream = pyte.ByteStream(self._screen)

    # ------------------------------------------------------------------
    # PTY 시작/중지
    # ------------------------------------------------------------------

    def start(self):
        """터미널 프로세스 시작 (CRealConsole::Start() 대응)"""
        if sys.platform == "win32":
            self._start_windows()
        else:
            self._start_unix()
        self._running = True
        self._repaint_timer.start()

    def _start_windows(self):
        """Windows PTY (pywinpty)"""
        try:
            import winpty  # pywinpty
            self._pty = winpty.PTY(self._cols, self._rows)
            shell = os.environ.get("COMSPEC", "cmd.exe")
            self._pty.spawn(shell)
        except ImportError:
            # pywinpty 없으면 subprocess fallback
            import subprocess
            self._pty = subprocess.Popen(
                ["cmd.exe"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        self._reader_thread = threading.Thread(
            target=self._read_loop_windows, daemon=True
        )
        self._reader_thread.start()

    def _start_unix(self):
        """Unix PTY (ptyprocess)"""
        try:
            import ptyprocess
            shell = os.environ.get("SHELL", "/bin/bash")
            self._pty = ptyprocess.PtyProcess.spawn([shell])
        except ImportError:
            import subprocess
            shell = os.environ.get("SHELL", "/bin/sh")
            self._pty = subprocess.Popen(
                [shell],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        self._reader_thread = threading.Thread(
            target=self._read_loop_unix, daemon=True
        )
        self._reader_thread.start()

    def stop(self):
        """터미널 프로세스 종료"""
        self._running = False
        self._repaint_timer.stop()
        if self._pty is not None:
            try:
                if sys.platform == "win32":
                    self._pty.close()
                else:
                    self._pty.terminate()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # PTY 읽기 루프
    # ------------------------------------------------------------------

    def _read_loop_windows(self):
        """Windows PTY 출력 읽기 루프 (ConEmuSrv 역할)"""
        import winpty
        while self._running:
            try:
                if isinstance(self._pty, winpty.PTY):
                    data = self._pty.read(4096)
                    if data:
                        self._feed(data.encode("utf-8", errors="replace"))
                else:
                    # subprocess fallback
                    data = self._pty.stdout.read(4096)
                    if not data:
                        break
                    self._feed(data)
            except Exception:
                break
        self.process_exited.emit()

    def _read_loop_unix(self):
        """Unix PTY 출력 읽기 루프"""
        while self._running:
            try:
                data = self._pty.read(4096)
                if not data:
                    break
                self._feed(data if isinstance(data, bytes) else data.encode())
            except Exception:
                break
        self.process_exited.emit()

    def _feed(self, data: bytes):
        """PTY 출력을 pyte 스트림에 공급 (ConAnsi 역할)"""
        if self._stream is not None:
            self._stream.feed(data)
            # 타이틀 변경 감지
            if self._screen and self._screen.title:
                self.title_changed.emit(self._screen.title)

    # ------------------------------------------------------------------
    # 렌더링 (CVirtualConsole::Paint() 대응)
    # ------------------------------------------------------------------

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setFont(self._font)

        # 전체 배경 채우기
        painter.fillRect(self.rect(), QColor(DEFAULT_BG))

        if self._screen is None:
            painter.setPen(QColor(DEFAULT_FG))
            painter.drawText(10, 20, "pyte 라이브러리가 필요합니다: pip install pyte")
            return

        fm = QFontMetrics(self._font)

        for row_idx in range(self._screen.lines):
            for col_idx in range(self._screen.columns):
                char = self._screen.buffer[row_idx][col_idx]

                fg = _resolve_color(char.fg, DEFAULT_FG)
                bg = _resolve_color(char.bg, DEFAULT_BG)

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

        # 커서 그리기
        if self._screen.cursor:
            cx = self._screen.cursor.x * self._cell_w
            cy = self._screen.cursor.y * self._cell_h
            painter.fillRect(cx, cy, self._cell_w, self._cell_h,
                             QColor("#ffffff"))
            # 커서 위치의 문자도 반전 렌더링
            char = self._screen.buffer[self._screen.cursor.y][self._screen.cursor.x]
            if char.data and char.data != " ":
                painter.setPen(QColor(DEFAULT_BG))
                painter.drawText(cx, cy + fm.ascent(), char.data)

    # ------------------------------------------------------------------
    # 키보드 입력 처리 (CRealConsole::ProcessKeyDown() 대응)
    # ------------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent):
        if self._pty is None:
            return

        key = event.key()
        text = event.text()
        mods = event.modifiers()

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
                self._write(b"\x03")
                return
            if key == Qt.Key.Key_D:
                self._write(b"\x04")
                return
            if key == Qt.Key.Key_L:
                self._write(b"\x0c")
                return
            if key == Qt.Key.Key_Z:
                self._write(b"\x1a")
                return

        data = VT_MAP.get(key)
        if data:
            self._write(data)
        elif text:
            self._write(text.encode("utf-8"))

    def _has_selection(self) -> bool:
        # TODO: 2단계 이후 선택 영역 구현
        return False

    def _write(self, data: bytes):
        """PTY에 데이터 쓰기"""
        if self._pty is None:
            return
        try:
            if sys.platform == "win32":
                import winpty
                if isinstance(self._pty, winpty.PTY):
                    self._pty.write(data.decode("utf-8", errors="replace"))
                else:
                    self._pty.stdin.write(data)
                    self._pty.stdin.flush()
            else:
                self._pty.write(data)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 창 크기 변경 처리
    # ------------------------------------------------------------------

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        w = max(1, event.size().width() // self._cell_w)
        h = max(1, event.size().height() // self._cell_h)
        if w != self._cols or h != self._rows:
            self._cols = w
            self._rows = h
            self._resize_pty(w, h)
            if self._screen is not None:
                self._screen.resize(h, w)

    def _resize_pty(self, cols: int, rows: int):
        """PTY 크기 갱신"""
        if self._pty is None:
            return
        try:
            if sys.platform == "win32":
                import winpty
                if isinstance(self._pty, winpty.PTY):
                    self._pty.set_size(cols, rows)
            else:
                self._pty.setwinsize(rows, cols)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 마우스 (기본 - 3단계에서 확장)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent):
        self.setFocus()
