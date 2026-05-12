"""
Windows XP Luna Blue 스타일 — MDI 타이틀바 그라디언트 및 전체 팔레트/QSS
"""

from __future__ import annotations

from PySide6.QtWidgets import QProxyStyle, QStyle, QApplication
from PySide6.QtGui import QColor, QLinearGradient, QPalette
from PySide6.QtCore import Qt

# ---------------------------------------------------------------------------
# XP Luna Blue 색상 상수
# ---------------------------------------------------------------------------
_XP_ACT_LEFT   = QColor("#0A246A")   # 활성 타이틀바 좌측 (진한 남색)
_XP_ACT_RIGHT  = QColor("#A6CAF0")   # 활성 타이틀바 우측 (하늘색)
_XP_INA_LEFT   = QColor("#7A96DF")   # 비활성 타이틀바 좌측
_XP_INA_RIGHT  = QColor("#C2D6F5")   # 비활성 타이틀바 우측
_XP_TEXT       = QColor("#FFFFFF")   # 타이틀 텍스트 (흰색)
_XP_BTN_FACE   = QColor("#D8E4F8")   # 버튼 배경 (연파랑)
_XP_BTN_BORDER = QColor("#003580")   # 버튼 테두리

# ---------------------------------------------------------------------------
# XP-like 전체 팔레트
# ---------------------------------------------------------------------------
_XP_PALETTE_COLORS: list[tuple] = [
    (QPalette.ColorGroup.All,      QPalette.ColorRole.Window,          "#ECE9D8"),
    (QPalette.ColorGroup.All,      QPalette.ColorRole.WindowText,      "#000000"),
    (QPalette.ColorGroup.All,      QPalette.ColorRole.Button,          "#D4D0C8"),
    (QPalette.ColorGroup.All,      QPalette.ColorRole.ButtonText,      "#000000"),
    (QPalette.ColorGroup.All,      QPalette.ColorRole.Base,            "#FFFFFF"),
    (QPalette.ColorGroup.All,      QPalette.ColorRole.AlternateBase,   "#F5F2EC"),
    (QPalette.ColorGroup.All,      QPalette.ColorRole.Highlight,       "#316AC5"),
    (QPalette.ColorGroup.All,      QPalette.ColorRole.HighlightedText, "#FFFFFF"),
    (QPalette.ColorGroup.All,      QPalette.ColorRole.Link,            "#0000CC"),
    (QPalette.ColorGroup.All,      QPalette.ColorRole.Mid,             "#C8C4BC"),
    (QPalette.ColorGroup.All,      QPalette.ColorRole.Dark,            "#919B9C"),
    (QPalette.ColorGroup.All,      QPalette.ColorRole.Light,           "#FFFFFF"),
    # 활성 타이틀바 힌트 (QMdiSubWindow 팔레트 fallback)
    (QPalette.ColorGroup.Active,   QPalette.ColorRole.Window,          "#0A246A"),
    (QPalette.ColorGroup.Active,   QPalette.ColorRole.WindowText,      "#FFFFFF"),
    (QPalette.ColorGroup.Inactive, QPalette.ColorRole.Window,          "#7A96DF"),
    (QPalette.ColorGroup.Inactive, QPalette.ColorRole.WindowText,      "#D8E8F8"),
]


def build_xp_palette() -> QPalette:
    """Windows XP Luna Blue 색상이 적용된 QPalette 반환."""
    pal = QPalette()
    for group, role, hex_color in _XP_PALETTE_COLORS:
        pal.setColor(group, role, QColor(hex_color))
    return pal


# ---------------------------------------------------------------------------
# QSS (Qt Stylesheet) — XP Luna Blue 위젯 스타일
# ---------------------------------------------------------------------------
XP_STYLESHEET = """
QMainWindow {
    background-color: #ECE9D8;
}

QMdiArea {
    background-color: #6A8ABD;
}

QMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:1 #D8D0C8);
    color: #000000;
    border-bottom: 1px solid #919B9C;
}
QMenuBar::item {
    padding: 2px 6px;
    background: transparent;
}
QMenuBar::item:selected,
QMenuBar::item:pressed {
    background: #316AC5;
    color: #FFFFFF;
}

QMenu {
    background-color: #FFFFFF;
    border: 1px solid #919B9C;
    padding: 2px;
}
QMenu::item {
    padding: 3px 20px;
    color: #000000;
}
QMenu::item:selected {
    background: #316AC5;
    color: #FFFFFF;
}
QMenu::separator {
    height: 1px;
    background: #D4D0C8;
    margin: 3px 0px;
}

QToolBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:1 #D8D0C8);
    border-bottom: 1px solid #919B9C;
    spacing: 3px;
    padding: 2px;
}

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:0.45 #ECE9D8, stop:0.5 #D4D0C8, stop:1 #C8C4BC);
    border: 1px solid #7F9DB9;
    border-radius: 3px;
    padding: 4px 10px;
    color: #000000;
    min-height: 20px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #EEF4FF, stop:0.45 #C8D8F8, stop:0.5 #A8C0F0, stop:1 #8AAAE8);
    border-color: #316AC5;
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #8AAAE8, stop:1 #C8D8F8);
}
QPushButton:default {
    border: 2px solid #316AC5;
}

QStatusBar {
    background: #ECE9D8;
    color: #000000;
    border-top: 1px solid #919B9C;
}

QScrollBar:vertical {
    background: #F0EDE8;
    width: 17px;
    border: 1px solid #ACA899;
}
QScrollBar::handle:vertical {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #D4D0C8, stop:1 #BCBBB6);
    min-height: 20px;
    border: 1px solid #ACA899;
}
QScrollBar:horizontal {
    background: #F0EDE8;
    height: 17px;
    border: 1px solid #ACA899;
}
QScrollBar::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #D4D0C8, stop:1 #BCBBB6);
    min-width: 20px;
    border: 1px solid #ACA899;
}

QLineEdit,
QTextEdit,
QPlainTextEdit {
    background: #FFFFFF;
    border: 1px solid #7F9DB9;
    selection-background-color: #316AC5;
    selection-color: #FFFFFF;
}

QLabel {
    color: #000000;
}

QDialog {
    background-color: #ECE9D8;
}

QGroupBox {
    border: 2px solid #D4D0C8;
    border-radius: 4px;
    margin-top: 8px;
    color: #000000;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 4px;
    color: #000000;
}

QTabWidget::pane {
    border: 1px solid #7F9DB9;
    background: #FFFFFF;
}
QTabBar::tab {
    background: #D4D0C8;
    border: 1px solid #919B9C;
    padding: 4px 8px;
    color: #000000;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    border-bottom-color: #FFFFFF;
}

QComboBox {
    background: #FFFFFF;
    border: 1px solid #7F9DB9;
    padding: 2px 4px;
    color: #000000;
    min-height: 20px;
}
QComboBox:hover {
    border-color: #316AC5;
}

QSpinBox {
    background: #FFFFFF;
    border: 1px solid #7F9DB9;
    padding: 2px;
    color: #000000;
}

QCheckBox {
    color: #000000;
    spacing: 5px;
}
QRadioButton {
    color: #000000;
    spacing: 5px;
}
"""

# ---------------------------------------------------------------------------
# XP 타이틀바 버튼 명세 (서브컨트롤 → 표준 픽스맵)
# ---------------------------------------------------------------------------
_TITLE_BTN_SPECS = (
    (QStyle.SubControl.SC_TitleBarCloseButton,
     QStyle.StandardPixmap.SP_TitleBarCloseButton),
    (QStyle.SubControl.SC_TitleBarMaxButton,
     QStyle.StandardPixmap.SP_TitleBarMaxButton),
    (QStyle.SubControl.SC_TitleBarMinButton,
     QStyle.StandardPixmap.SP_TitleBarMinButton),
    (QStyle.SubControl.SC_TitleBarNormalButton,
     QStyle.StandardPixmap.SP_TitleBarNormalButton),
)


# ---------------------------------------------------------------------------
# QProxyStyle — MDI 서브윈도우 타이틀바 XP 그라디언트 커스텀 드로잉
# ---------------------------------------------------------------------------
class XPTitleBarStyle(QProxyStyle):
    """
    QMdiSubWindow 타이틀바를 Windows XP Luna Blue 그라디언트로 그리는 프록시 스타일.
    그 외 모든 위젯 그리기는 기반 스타일(Fusion)에 위임한다.
    """

    def drawComplexControl(self, cc, opt, painter, widget=None):
        if cc != QStyle.ComplexControl.CC_TitleBar:
            super().drawComplexControl(cc, opt, painter, widget)
            return

        active = bool(opt.state & QStyle.StateFlag.State_Active)
        r = opt.rect

        # 1. 그라디언트 배경
        grad = QLinearGradient(r.left(), r.top(), r.right(), r.top())
        if active:
            grad.setColorAt(0.0, _XP_ACT_LEFT)
            grad.setColorAt(1.0, _XP_ACT_RIGHT)
        else:
            grad.setColorAt(0.0, _XP_INA_LEFT)
            grad.setColorAt(1.0, _XP_INA_RIGHT)
        painter.fillRect(r, grad)

        # 2. 창 아이콘 (시스템 메뉴 버튼 자리)
        if opt.subControls & QStyle.SubControl.SC_TitleBarSysMenu:
            sys_rect = self.subControlRect(
                cc, opt, QStyle.SubControl.SC_TitleBarSysMenu, widget
            )
            if sys_rect.isValid() and not opt.icon.isNull():
                opt.icon.paint(painter, sys_rect)

        # 3. 타이틀 텍스트
        label_rect = self.subControlRect(
            cc, opt, QStyle.SubControl.SC_TitleBarLabel, widget
        )
        if label_rect.isValid() and opt.text:
            painter.save()
            f = painter.font()
            f.setBold(True)
            painter.setFont(f)
            painter.setPen(_XP_TEXT)
            painter.drawText(
                label_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                opt.text,
            )
            painter.restore()

        # 4. 타이틀바 버튼 (닫기 / 최대화 / 최소화 / 복원)
        for sc, px_id in _TITLE_BTN_SPECS:
            if not (opt.subControls & sc):
                continue
            btn_rect = self.subControlRect(cc, opt, sc, widget)
            if not btn_rect.isValid() or btn_rect.isEmpty():
                continue
            pressed = bool(opt.activeSubControls & sc)
            painter.save()
            bg = _XP_BTN_FACE.darker(115) if pressed else _XP_BTN_FACE
            painter.fillRect(btn_rect, bg)
            painter.setPen(_XP_BTN_BORDER)
            painter.drawRect(btn_rect.adjusted(0, 0, -1, -1))
            px = self.standardPixmap(px_id, opt, widget)
            if not px.isNull():
                inner = btn_rect.adjusted(3, 3, -3, -3)
                painter.drawPixmap(
                    inner,
                    px.scaled(
                        inner.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ),
                )
            painter.restore()


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------
def apply_xp_style(app: QApplication) -> None:
    """QApplication에 Windows XP Luna Blue 스타일을 전체 적용한다."""
    app.setStyle(XPTitleBarStyle("Fusion"))
    app.setPalette(build_xp_palette())
    app.setStyleSheet(XP_STYLESHEET)
