"""
ConEmu Python 변환 - 설정 다이얼로그 (Set*.cpp 대응)

원본 ConEmu의 설정 창(IDD_SETTINGS)과 각 페이지(SetPg*)를 PyQt6로 구현.

페이지 구성 (thi_* enum 대응):
  General    (thi_General)  - 일반: 시작 셸, 스크롤백
  Fonts      (thi_Fonts)    - 폰트: 패밀리·크기·굵기
  Colors     (thi_Colors)   - 색상: ANSI 팔레트, 기본 FG/BG
  Appearance (thi_Appear)   - 모양: 탭 위치, 창 타이틀
  Cursor     (thi_Cursor)   - 커서: 스타일·깜빡임
  Keyboard   (thi_Keyboard) - 단축키: 키 바인딩 목록
"""

import sys
from typing import Callable

from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QWidget, QLabel, QLineEdit, QSpinBox, QCheckBox,
    QComboBox, QPushButton, QDialogButtonBox, QGroupBox, QGridLayout,
    QColorDialog, QFontDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette

from config.settings import AppSettings

# 설정 변경을 외부에 알리는 모듈 레벨 시그널 에뮬레이션
# (TerminalView 등이 settings_changed 콜백을 등록)
_change_callbacks: list[Callable[[], None]] = []


def register_settings_changed(callback: Callable[[], None]) -> None:
    """설정 변경 콜백 등록 (모든 TerminalView가 폰트/색상 갱신할 때 사용)"""
    _change_callbacks.append(callback)


def _notify_settings_changed() -> None:
    for cb in _change_callbacks:
        try:
            cb()
        except Exception as e:
            print(f"[ERROR][settings_dialog] 콜백 오류: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# 공통 헬퍼 위젯
# ──────────────────────────────────────────────────────────────────────────────

class _ColorButton(QPushButton):
    """색상 선택 버튼 — 클릭하면 QColorDialog 열림"""
    color_changed = pyqtSignal(str)   # 새 hex 색상 문자열

    def __init__(self, color: str = "#000000", parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 20)
        self.set_color(color)
        self.clicked.connect(self._pick)

    def set_color(self, hex_color: str) -> None:
        self._color = hex_color
        self.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #888;")

    def get_color(self) -> str:
        return self._color

    def _pick(self):
        c = QColorDialog.getColor(QColor(self._color), self, "색상 선택")
        if c.isValid():
            self.set_color(c.name())
            self.color_changed.emit(c.name())


def _section_label(text: str) -> QLabel:
    lbl = QLabel(f"<b>{text}</b>")
    lbl.setStyleSheet("color: #555; margin-top: 6px;")
    return lbl


# ──────────────────────────────────────────────────────────────────────────────
# 설정 페이지 기반 클래스
# ──────────────────────────────────────────────────────────────────────────────

class _BasePage(QWidget):
    """모든 설정 페이지의 기반. apply()를 구현해야 함."""

    def apply(self, settings: AppSettings) -> None:  # noqa: ARG002
        """UI 값을 AppSettings에 반영"""

    def load(self, settings: AppSettings) -> None:  # noqa: ARG002
        """AppSettings 값을 UI에 로드"""


# ──────────────────────────────────────────────────────────────────────────────
# 1. General 페이지 (CSetPgGeneral)
# ──────────────────────────────────────────────────────────────────────────────

class _GeneralPage(_BasePage):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(_section_label("시작 셸 (Startup Shell)"))

        # 시작 셸 입력
        self._shell_edit = QLineEdit()
        self._shell_edit.setPlaceholderText("비워두면 OS 기본 셸 (cmd.exe / bash)")
        layout.addWidget(self._shell_edit)

        layout.addWidget(_section_label("스크롤백 버퍼"))
        row = QHBoxLayout()
        row.addWidget(QLabel("최대 줄 수:"))
        self._scroll_spin = QSpinBox()
        self._scroll_spin.setRange(100, 100000)
        self._scroll_spin.setSingleStep(1000)
        row.addWidget(self._scroll_spin)
        row.addStretch()
        layout.addLayout(row)

        layout.addWidget(_section_label("기타"))
        self._save_on_exit = QCheckBox("종료 시 설정 자동 저장")
        layout.addWidget(self._save_on_exit)

        layout.addStretch()

    def load(self, s: AppSettings):
        self._shell_edit.setText(s.startup_shell)
        self._scroll_spin.setValue(s.scrollback_lines)
        self._save_on_exit.setChecked(s.save_on_exit)

    def apply(self, s: AppSettings):
        s.startup_shell = self._shell_edit.text().strip()
        s.scrollback_lines = self._scroll_spin.value()
        s.save_on_exit = self._save_on_exit.isChecked()


# ──────────────────────────────────────────────────────────────────────────────
# 2. Fonts 페이지 (CSetPgFonts)
# ──────────────────────────────────────────────────────────────────────────────

class _FontsPage(_BasePage):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(_section_label("터미널 폰트"))

        # 폰트 선택 버튼
        self._font_btn = QPushButton("폰트 선택…")
        self._font_btn.clicked.connect(self._pick_font)
        layout.addWidget(self._font_btn)

        # 미리보기
        self._preview = QLabel("AaBbCcDdEe 0123456789")
        self._preview.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        self._preview.setMinimumHeight(50)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._preview)

        # 세부 제어
        grid = QGridLayout()
        grid.addWidget(QLabel("패밀리:"), 0, 0)
        self._family_label = QLabel()
        grid.addWidget(self._family_label, 0, 1)

        grid.addWidget(QLabel("크기:"), 1, 0)
        self._size_spin = QSpinBox()
        self._size_spin.setRange(6, 72)
        self._size_spin.valueChanged.connect(self._update_preview)
        grid.addWidget(self._size_spin, 1, 1)

        self._bold_cb = QCheckBox("굵게 (Bold)")
        self._bold_cb.stateChanged.connect(self._update_preview)
        grid.addWidget(self._bold_cb, 2, 0, 1, 2)

        layout.addLayout(grid)
        layout.addStretch()

        self._family = ""

    def _pick_font(self):
        font = QFont(self._family, self._size_spin.value())
        font.setBold(self._bold_cb.isChecked())
        ok, selected = QFontDialog.getFont(font, self, "폰트 선택")
        if ok:
            self._family = selected.family()
            self._family_label.setText(self._family)
            self._size_spin.setValue(selected.pointSize())
            self._bold_cb.setChecked(selected.bold())
            self._update_preview()

    def _update_preview(self):
        f = QFont(self._family, self._size_spin.value())
        f.setBold(self._bold_cb.isChecked())
        self._preview.setFont(f)
        self._family_label.setText(self._family)

    def load(self, s: AppSettings):
        self._family = s.font_family
        self._size_spin.setValue(s.font_size)
        self._bold_cb.setChecked(s.font_bold)
        self._update_preview()

    def apply(self, s: AppSettings):
        s.font_family = self._family
        s.font_size = self._size_spin.value()
        s.font_bold = self._bold_cb.isChecked()


# ──────────────────────────────────────────────────────────────────────────────
# 3. Colors 페이지 (CSetPgColors)
# ──────────────────────────────────────────────────────────────────────────────

_COLOR_NAMES = [
    "0: Black",        "1: Dark Red",     "2: Dark Green",  "3: Dark Yellow",
    "4: Dark Blue",    "5: Dark Magenta", "6: Dark Cyan",   "7: Light Gray",
    "8: Dark Gray",    "9: Bright Red",   "10: Bright Green","11: Bright Yellow",
    "12: Bright Blue", "13: Bright Magenta","14: Bright Cyan","15: White",
]


class _ColorsPage(_BasePage):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 기본 전경/배경
        layout.addWidget(_section_label("기본 색상"))
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("기본 전경색 (FG):"))
        self._fg_btn = _ColorButton()
        row1.addWidget(self._fg_btn)
        row1.addSpacing(20)
        row1.addWidget(QLabel("기본 배경색 (BG):"))
        self._bg_btn = _ColorButton()
        row1.addWidget(self._bg_btn)
        row1.addStretch()
        layout.addLayout(row1)

        # ANSI 16색 팔레트
        layout.addWidget(_section_label("ANSI 16색 팔레트"))
        self._palette_btns: list[_ColorButton] = []
        grid = QGridLayout()
        grid.setSpacing(4)
        for i in range(16):
            lbl = QLabel(_COLOR_NAMES[i])
            lbl.setMinimumWidth(140)
            btn = _ColorButton()
            self._palette_btns.append(btn)
            row, col = divmod(i, 2)
            grid.addWidget(lbl, row, col * 2)
            grid.addWidget(btn, row, col * 2 + 1)
        layout.addLayout(grid)
        layout.addStretch()

    def load(self, s: AppSettings):
        self._fg_btn.set_color(s.default_fg)
        self._bg_btn.set_color(s.default_bg)
        pal = s.palette
        for i, btn in enumerate(self._palette_btns):
            btn.set_color(pal[i])

    def apply(self, s: AppSettings):
        s.default_fg = self._fg_btn.get_color()
        s.default_bg = self._bg_btn.get_color()
        s.palette = [btn.get_color() for btn in self._palette_btns]


# ──────────────────────────────────────────────────────────────────────────────
# 4. Appearance 페이지 (CSetPgAppear)
# ──────────────────────────────────────────────────────────────────────────────

class _AppearancePage(_BasePage):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(_section_label("창 제목"))
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("ConEmu-Py")
        layout.addWidget(self._title_edit)

        layout.addWidget(_section_label("탭 표시"))
        row = QHBoxLayout()
        row.addWidget(QLabel("탭 위치:"))
        self._tab_pos = QComboBox()
        self._tab_pos.addItems(["위 (Top)", "아래 (Bottom)"])
        row.addWidget(self._tab_pos)
        row.addStretch()
        layout.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("탭 타이틀 형식:"))
        self._tab_fmt = QLineEdit()
        self._tab_fmt.setPlaceholderText("%s")
        row2.addWidget(self._tab_fmt)
        layout.addLayout(row2)

        layout.addStretch()

    def load(self, s: AppSettings):
        self._title_edit.setText(s.window_title)
        self._tab_pos.setCurrentIndex(0 if s.tab_position == "top" else 1)
        self._tab_fmt.setText(s.tab_title_fmt)

    def apply(self, s: AppSettings):
        s.window_title = self._title_edit.text().strip() or "ConEmu-Py"
        s.tab_position = "top" if self._tab_pos.currentIndex() == 0 else "bottom"
        s.tab_title_fmt = self._tab_fmt.text().strip() or "%s"


# ──────────────────────────────────────────────────────────────────────────────
# 5. Cursor 페이지 (CSetPgCursor)
# ──────────────────────────────────────────────────────────────────────────────

class _CursorPage(_BasePage):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(_section_label("커서 스타일"))
        self._style_combo = QComboBox()
        self._style_combo.addItems(["블록 (Block)", "밑줄 (Underline)", "막대 (Bar)"])
        layout.addWidget(self._style_combo)

        self._blink_cb = QCheckBox("커서 깜빡임 (Blink)")
        layout.addWidget(self._blink_cb)

        # 미리보기 라벨
        layout.addWidget(_section_label("미리보기"))
        self._preview = QLabel("커서 미리보기: ▌")
        self._preview.setStyleSheet("font-size: 18px; padding: 8px;")
        layout.addWidget(self._preview)
        self._style_combo.currentIndexChanged.connect(self._update_preview)

        layout.addStretch()

    def _update_preview(self, idx: int = -1):
        idx = self._style_combo.currentIndex()
        symbols = ["█", "_", "|"]
        self._preview.setText(f"커서 미리보기: {symbols[idx]}")

    def load(self, s: AppSettings):
        idx = {"block": 0, "underline": 1, "bar": 2}.get(s.cursor_style, 0)
        self._style_combo.setCurrentIndex(idx)
        self._blink_cb.setChecked(s.cursor_blink)
        self._update_preview()

    def apply(self, s: AppSettings):
        styles = ["block", "underline", "bar"]
        s.cursor_style = styles[self._style_combo.currentIndex()]
        s.cursor_blink = self._blink_cb.isChecked()


# ──────────────────────────────────────────────────────────────────────────────
# 6. Keyboard 페이지 (CSetPgKeyboard)
# ──────────────────────────────────────────────────────────────────────────────

_SHORTCUT_LABELS = {
    "new_tab":     "새 탭 열기",
    "close_tab":   "탭 닫기",
    "settings":    "설정 열기",
    "copy":        "복사",
    "paste":       "붙여넣기",
    "find":        "찾기",
    "next_tab":    "다음 탭",
    "prev_tab":    "이전 탭",
}


class _KeyboardPage(_BasePage):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_section_label("단축키 설정"))

        self._table = QTableWidget(len(_SHORTCUT_LABELS), 2)
        self._table.setHorizontalHeaderLabels(["기능", "단축키"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self._actions = list(_SHORTCUT_LABELS.keys())
        for row, action in enumerate(self._actions):
            label_item = QTableWidgetItem(_SHORTCUT_LABELS[action])
            label_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(row, 0, label_item)
            self._table.setItem(row, 1, QTableWidgetItem(""))

        layout.addWidget(self._table)

        note = QLabel(
            "※ 단축키를 변경한 후 [적용] 또는 [확인]을 눌러야 반영됩니다.\n"
            "   단축키 충돌은 자동으로 감지되지 않습니다."
        )
        note.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(note)

    def load(self, s: AppSettings):
        sc = s.shortcuts
        for row, action in enumerate(self._actions):
            item = self._table.item(row, 1)
            if item is not None:
                item.setText(sc.get(action, ""))

    def apply(self, s: AppSettings):
        for row, action in enumerate(self._actions):
            item = self._table.item(row, 1)
            if item is not None:
                s.set_shortcut(action, item.text().strip())


# ──────────────────────────────────────────────────────────────────────────────
# 메인 설정 다이얼로그 (IDD_SETTINGS 대응)
# ──────────────────────────────────────────────────────────────────────────────

_PAGES = [
    ("일반 (General)",       _GeneralPage),
    ("폰트 (Fonts)",         _FontsPage),
    ("색상 (Colors)",        _ColorsPage),
    ("모양 (Appearance)",    _AppearancePage),
    ("커서 (Cursor)",        _CursorPage),
    ("단축키 (Keyboard)",    _KeyboardPage),
]


class SettingsDialog(QDialog):
    """
    ConEmu 설정 다이얼로그.
    원본 IDD_SETTINGS 다이얼로그 + 각 CSetPg* 페이지 대응.

    사용::
        dlg = SettingsDialog(parent)
        if dlg.exec():
            pass  # 설정 적용 완료
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ConEmu-Py 설정")
        self.setMinimumSize(680, 500)
        self.resize(780, 560)
        self._settings = AppSettings.instance()
        self._pages: list[_BasePage] = []
        self._init_ui()
        self._load_all()

    # ------------------------------------------------------------------
    # UI 초기화
    # ------------------------------------------------------------------

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # ── 상단: 페이지 목록 + 내용 ──────────────────────────────────
        content_layout = QHBoxLayout()

        # 왼쪽: 페이지 목록 (QListWidget)
        self._page_list = QListWidget()
        self._page_list.setFixedWidth(170)
        self._page_list.setStyleSheet(
            "QListWidget { border: 1px solid #ccc; font-size: 12px; }"
            "QListWidget::item { padding: 6px 8px; }"
            "QListWidget::item:selected { background: #0078d4; color: white; }"
        )

        # 오른쪽: 페이지 스택
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("QStackedWidget { border: 1px solid #ccc; padding: 8px; }")

        for name, PageClass in _PAGES:
            self._page_list.addItem(QListWidgetItem(name))
            page = PageClass()
            self._pages.append(page)
            self._stack.addWidget(page)

        self._page_list.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._page_list.setCurrentRow(0)

        content_layout.addWidget(self._page_list)
        content_layout.addWidget(self._stack, 1)
        main_layout.addLayout(content_layout)

        # ── 하단: 버튼 바 ─────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(sep)

        btn_layout = QHBoxLayout()

        # 도움말 링크 (원본 ConEmu wiki 링크 대응)
        help_btn = QPushButton("온라인 도움말")
        help_btn.setFlat(True)
        help_btn.setStyleSheet("color: #0078d4; text-decoration: underline;")
        help_btn.clicked.connect(self._open_help)
        btn_layout.addWidget(help_btn)
        btn_layout.addStretch()

        self._btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._btn_box.accepted.connect(self._on_ok)
        self._btn_box.rejected.connect(self.reject)
        self._btn_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self._on_apply
        )
        btn_layout.addWidget(self._btn_box)
        main_layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # 로드 / 적용
    # ------------------------------------------------------------------

    def _load_all(self):
        """모든 페이지에 현재 설정 값 로드"""
        for page in self._pages:
            page.load(self._settings)

    def _apply_all(self):
        """모든 페이지의 UI 값을 AppSettings에 반영하고 저장"""
        for page in self._pages:
            page.apply(self._settings)
        self._settings.save()
        _notify_settings_changed()
        print("[LOG][SettingsDialog] 설정 적용 완료")

    def _on_ok(self):
        self._apply_all()
        self.accept()

    def _on_apply(self):
        self._apply_all()

    def _open_help(self):
        import webbrowser
        webbrowser.open("https://conemu.github.io/en/Settings.html")
