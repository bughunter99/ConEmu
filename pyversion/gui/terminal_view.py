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
import traceback

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QKeyEvent,
    QMouseEvent, QPaintEvent, QResizeEvent, QClipboard
)

try:
    import pyte
    try:
        from importlib.metadata import version as _pkg_version
        _pyte_ver = _pkg_version("pyte")
    except Exception:
        _pyte_ver = "알 수 없음"
    print("[DEBUG] pyte 임포트 성공, 버전:", _pyte_ver)
except ImportError:
    pyte = None  # type: ignore
    print("[ERROR] pyte 임포트 실패 - 'pip install pyte' 를 실행하세요")

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
        from PyQt6.QtGui import QFontDatabase
        available = set(QFontDatabase.families())
        for name in TerminalView._FONT_CANDIDATES:
            if name in available:
                font = QFont(name, size)
                font.setFixedPitch(True)
                print(f"[DEBUG] _pick_font: '{name}' 사용")
                return font
        # 하나도 없으면 Qt 기본 고정폭 폰트
        print("[WARN] _pick_font: 후보 폰트 없음, QFontDatabase.systemFont(FixedFont) 사용")
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(size)
        return font

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setCursor(Qt.CursorShape.IBeamCursor)

        # 폰트 (CFontMgr 대응) — 시스템에 따라 적절한 폰트 선택
        self._font = self._pick_font(11)
        print(f"[DEBUG] __init__: 폰트 선택됨 → {self._font.family()} {self._font.pointSize()}pt")
        fm = QFontMetrics(self._font)
        self._cell_w = fm.horizontalAdvance("M")
        self._cell_h = fm.height()
        print(f"[DEBUG] __init__: 셀 크기 → {self._cell_w}x{self._cell_h}px")

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
            print("[ERROR] _init_pyte: pyte가 없어서 버퍼를 초기화할 수 없습니다.")
            return
        self._screen = pyte.Screen(self._cols, self._rows)
        self._stream = pyte.ByteStream(self._screen)
        print(f"[DEBUG] _init_pyte: 화면 버퍼 생성 완료 ({self._cols}열 x {self._rows}행)")

    # ------------------------------------------------------------------
    # PTY 시작/중지
    # ------------------------------------------------------------------

    def start(self):
        """터미널 프로세스 시작 (CRealConsole::Start() 대응)"""
        print(f"[DEBUG] start: 플랫폼={sys.platform}")
        if sys.platform == "win32":
            self._start_windows()
        else:
            self._start_unix()
        self._running = True
        self._repaint_timer.start()
        print(f"[DEBUG] start: repaint 타이머 시작, _pty={self._pty}")

    def _start_windows(self):
        """Windows PTY (pywinpty)"""
        try:
            import winpty  # pywinpty
            print("[DEBUG] _start_windows: pywinpty 임포트 성공")
            self._pty = winpty.PTY(self._cols, self._rows)
            shell = os.environ.get("COMSPEC", "cmd.exe")
            print(f"[DEBUG] _start_windows: 쉘 실행 → {shell}")
            self._pty.spawn(shell)
            print("[DEBUG] _start_windows: PTY spawn 완료")
        except ImportError:
            print("[WARN] _start_windows: pywinpty 없음, subprocess fallback 사용")
            import subprocess
            self._pty = subprocess.Popen(
                ["cmd.exe"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            print(f"[DEBUG] _start_windows: subprocess PID={self._pty.pid}")
        except Exception as e:
            print(f"[ERROR] _start_windows: PTY 시작 실패 → {e}")
            traceback.print_exc()
            return
        self._reader_thread = threading.Thread(
            target=self._read_loop_windows, daemon=True
        )
        self._reader_thread.start()
        print("[DEBUG] _start_windows: 읽기 스레드 시작됨")

    def _start_unix(self):
        """Unix PTY (ptyprocess)"""
        try:
            import ptyprocess
            print("[DEBUG] _start_unix: ptyprocess 임포트 성공")
            shell = os.environ.get("SHELL", "/bin/bash")
            print(f"[DEBUG] _start_unix: 쉘 실행 → {shell}")
            self._pty = ptyprocess.PtyProcess.spawn([shell])
            print(f"[DEBUG] _start_unix: PTY spawn 완료, PID={self._pty.pid}")
        except ImportError:
            print("[WARN] _start_unix: ptyprocess 없음, subprocess fallback 사용")
            print("[WARN]   → 'pip install ptyprocess' 설치를 권장합니다")
            import subprocess
            shell = os.environ.get("SHELL", "/bin/sh")
            print(f"[DEBUG] _start_unix: subprocess로 {shell} 실행")
            self._pty = subprocess.Popen(
                [shell],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            print(f"[DEBUG] _start_unix: subprocess PID={self._pty.pid}")
        except Exception as e:
            print(f"[ERROR] _start_unix: PTY 시작 실패 → {e}")
            traceback.print_exc()
            return
        self._reader_thread = threading.Thread(
            target=self._read_loop_unix, daemon=True
        )
        self._reader_thread.start()
        print("[DEBUG] _start_unix: 읽기 스레드 시작됨")

    def stop(self):
        """터미널 프로세스 종료"""
        print("[DEBUG] stop: 터미널 종료 요청")
        self._running = False
        self._repaint_timer.stop()
        if self._pty is not None:
            try:
                if sys.platform == "win32":
                    self._pty.close()
                else:
                    self._pty.terminate()
                print("[DEBUG] stop: PTY 종료 완료")
            except Exception as e:
                print(f"[WARN] stop: PTY 종료 중 오류 → {e}")

    # ------------------------------------------------------------------
    # PTY 읽기 루프
    # ------------------------------------------------------------------

    def _read_loop_windows(self):
        """Windows PTY 출력 읽기 루프 (ConEmuSrv 역할)"""
        print("[DEBUG] _read_loop_windows: 읽기 루프 시작")
        import winpty
        read_count = 0
        while self._running:
            try:
                if isinstance(self._pty, winpty.PTY):
                    data = self._pty.read(4096)
                    if data:
                        read_count += 1
                        if read_count <= 5:
                            print(f"[DEBUG] _read_loop_windows: 데이터 수신 #{read_count}, {len(data)}바이트")
                        self._feed(data.encode("utf-8", errors="replace"))
                else:
                    # subprocess fallback
                    data = self._pty.stdout.read(4096)
                    if not data:
                        print("[DEBUG] _read_loop_windows: subprocess stdout EOF")
                        break
                    read_count += 1
                    if read_count <= 5:
                        print(f"[DEBUG] _read_loop_windows: subprocess 데이터 #{read_count}, {len(data)}바이트")
                    self._feed(data)
            except Exception as e:
                print(f"[ERROR] _read_loop_windows: 읽기 오류 → {e}")
                traceback.print_exc()
                break
        print(f"[DEBUG] _read_loop_windows: 루프 종료 (총 {read_count}회 읽음)")
        self.process_exited.emit()

    def _read_loop_unix(self):
        """Unix PTY 출력 읽기 루프"""
        import subprocess
        is_subprocess = isinstance(self._pty, subprocess.Popen)
        print(f"[DEBUG] _read_loop_unix: 루프 시작, subprocess모드={is_subprocess}")
        read_count = 0
        while self._running:
            try:
                if is_subprocess:
                    # subprocess.Popen은 stdout.read()를 사용해야 함
                    data = self._pty.stdout.read(4096)
                else:
                    data = self._pty.read(4096)
                if not data:
                    print("[DEBUG] _read_loop_unix: EOF 수신, 루프 종료")
                    break
                read_count += 1
                if read_count <= 5:
                    print(f"[DEBUG] _read_loop_unix: 데이터 수신 #{read_count}, {len(data)}바이트, 내용(앞30)={data[:30]!r}")
                self._feed(data if isinstance(data, bytes) else data.encode())
            except Exception as e:
                print(f"[ERROR] _read_loop_unix: 읽기 오류 → {e}")
                traceback.print_exc()
                break
        print(f"[DEBUG] _read_loop_unix: 루프 종료 (총 {read_count}회 읽음)")
        self.process_exited.emit()

    def _feed(self, data: bytes):
        """PTY 출력을 pyte 스트림에 공급 (ConAnsi 역할)"""
        if self._stream is not None:
            self._stream.feed(data)
            # 타이틀 변경 감지
            if self._screen and self._screen.title:
                self.title_changed.emit(self._screen.title)
        else:
            print("[WARN] _feed: _stream이 None이라 데이터를 버립니다")

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
        rendered_chars = 0

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
                    rendered_chars += 1

        # 처음 몇 번만 렌더링 통계 출력
        if not hasattr(self, "_paint_count"):
            self._paint_count = 0
        self._paint_count += 1
        if self._paint_count <= 3 or rendered_chars > 0 and self._paint_count % 60 == 0:
            print(f"[DEBUG] paintEvent #{self._paint_count}: 셀크기=({self._cell_w}x{self._cell_h}), "
                  f"화면크기=({self._screen.columns}x{self._screen.lines}), "
                  f"렌더된 문자={rendered_chars}개, "
                  f"_running={self._running}")

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
            print("[WARN] keyPressEvent: _pty가 None입니다 (프로세스 없음)")
            return

        key = event.key()
        text = event.text()
        mods = event.modifiers()
        print(f"[DEBUG] keyPressEvent: key={key}, text={text!r}, mods={int(mods)}, _running={self._running}")

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
            print(f"[DEBUG] keyPressEvent: VT시퀀스 전송 {data!r}")
            self._write(data)
        elif text:
            print(f"[DEBUG] keyPressEvent: 텍스트 전송 {text!r}")
            self._write(text.encode("utf-8"))
        else:
            print(f"[DEBUG] keyPressEvent: 매핑 없는 키 무시 (key={key})")

    def _has_selection(self) -> bool:
        # TODO: 2단계 이후 선택 영역 구현
        return False

    def _write(self, data: bytes):
        """PTY에 데이터 쓰기"""
        if self._pty is None:
            print("[WARN] _write: _pty가 None이라 쓰기 불가")
            return
        try:
            import subprocess
            if sys.platform == "win32":
                import winpty
                if isinstance(self._pty, winpty.PTY):
                    self._pty.write(data.decode("utf-8", errors="replace"))
                else:
                    # subprocess.Popen fallback
                    self._pty.stdin.write(data)
                    self._pty.stdin.flush()
            else:
                if isinstance(self._pty, subprocess.Popen):
                    # subprocess fallback: stdin은 bytes 모드
                    self._pty.stdin.write(data)
                    self._pty.stdin.flush()
                else:
                    # ptyprocess.PtyProcess.write()는 str을 받음
                    self._pty.write(data.decode("utf-8", errors="replace"))
        except Exception as e:
            print(f"[ERROR] _write: 쓰기 실패 → {e}")
            traceback.print_exc()

    # ------------------------------------------------------------------
    # 창 크기 변경 처리
    # ------------------------------------------------------------------

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        w = max(1, event.size().width() // self._cell_w)
        h = max(1, event.size().height() // self._cell_h)
        if w != self._cols or h != self._rows:
            print(f"[DEBUG] resizeEvent: 창 크기 변경 → {self._cols}x{self._rows} → {w}x{h}")
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
            print(f"[DEBUG] _resize_pty: PTY 크기 → {cols}x{rows}")
        except Exception as e:
            print(f"[WARN] _resize_pty: 크기 변경 실패 → {e}")

    # ------------------------------------------------------------------
    # 마우스 (기본 - 3단계에서 확장)
    # ------------------------------------------------------------------

    def sizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(self._cols * self._cell_w, self._rows * self._cell_h)

    def mousePressEvent(self, event: QMouseEvent):
        self.setFocus()
