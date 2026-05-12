"""
ConEmu Python 변환 - 메인 애플리케이션 창
CConEmuMain 클래스 대응 (1단계 프로토타입)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

print(f"[LOG][app.py] 모듈 로딩 시작 — Python {sys.version}")

from PySide6.QtWidgets import (
    QMainWindow,
    QMdiArea,
    QMdiSubWindow,
    QStatusBar,
    QToolBar,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QIcon

from gui.terminal_view import TerminalView
from gui.settings_dialog import SettingsDialog, register_settings_changed
from config.settings import AppSettings

print("[LOG][app.py] 모듈 로딩 완료")

_MIN_VERTICAL_TILE_WIDTH = 32
_MIN_HORIZONTAL_TILE_HEIGHT = 24
_ICON_CANDIDATES: dict[str, list[str]] = {
    "new": [
        "src/ConEmu/Far.ico",
        "logo/logo-32.png",
    ],
    "close": [
        "src/ConEmu/ConEmu15.ico",
        "logo/logo-24.png",
    ],
    "settings": [
        "src/ConEmu/ConEmu.ico",
        "logo/logo-16.png",
    ],
    "cascade": [
        "src/ConEmu/Search.ico",
        "logo/logo-20.png",
    ],
    "tile": [
        "logo/logo-40.png",
        "logo/logo-32.png",
    ],
}


class _TerminalSubWindow(QMdiSubWindow):
    def __init__(self, view: TerminalView, on_close: Callable[[TerminalView, _TerminalSubWindow], None], parent=None):
        super().__init__(parent)
        self._view = view
        self._on_close = on_close
        self.setWidget(view)
        self.setWindowIcon(QIcon())
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

    def closeEvent(self, event):
        if self._view is not None:
            print(f"[LOG][_TerminalSubWindow.closeEvent] view.stop() 호출: {self._view!r}")
            self._view.stop()
            self._on_close(self._view, self)
            self._view = None
        super().closeEvent(event)


class ConEmuApp(QMainWindow):
    """
    메인 애플리케이션 창.
    C++ CConEmuMain 클래스의 Python 대응.
    """

    def __init__(self):
        print("[LOG][ConEmuApp.__init__] 앱 창 생성 시작")
        super().__init__()
        self._settings = AppSettings.instance()
        self._tabs: list[TerminalView] = []
        self._sub_windows: list[_TerminalSubWindow] = []
        self._is_shutting_down = False
        print("[LOG][ConEmuApp.__init__] AppSettings 로드 완료")

        self._init_ui()
        self._init_menu()
        self._init_toolbar()
        self._init_shortcuts()
        self._apply_settings()

        register_settings_changed(self._apply_settings)

        print("[LOG][ConEmuApp.__init__] 첫 번째 콘솔 창 자동 생성 시작")
        self.new_tab()
        print("[LOG][ConEmuApp.__init__] 초기화 완료")

    def _init_ui(self):
        """창 레이아웃 초기화"""
        print("[LOG][_init_ui] 호출")
        self.mdi_area = QMdiArea(self)
        self.mdi_area.setViewMode(QMdiArea.ViewMode.SubWindowView)
        # MDI child window 기반 동작을 사용하므로 tabbed view 관련 옵션은 비활성화
        self.mdi_area.setTabsClosable(False)
        self.mdi_area.setTabsMovable(False)
        self.setCentralWidget(self.mdi_area)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("준비")
        print("[LOG][_init_ui] 완료 — QMdiArea, QStatusBar 생성됨")

    def _init_menu(self):
        """메뉴 바 초기화 (CConEmuMenu 대응)"""
        print("[LOG][_init_menu] 호출")
        menubar = self.menuBar()

        self._new_action = QAction("새 콘솔 창(&N)", self)
        self._new_action.setIcon(self._icon_for("new"))
        self._new_action.triggered.connect(self.new_tab)

        self._close_action = QAction("현재 창 닫기(&W)", self)
        self._close_action.setIcon(self._icon_for("close"))
        self._close_action.triggered.connect(self._close_current_tab)

        self._close_all_action = QAction("모든 창 닫기(&L)", self)
        self._close_all_action.triggered.connect(self._close_all_windows)

        self._quit_action = QAction("종료(&Q)", self)
        self._quit_action.triggered.connect(self.close)

        self._settings_action = QAction("설정(&S)…", self)
        self._settings_action.setIcon(self._icon_for("settings"))
        self._settings_action.triggered.connect(self.open_settings)

        self._cascade_action = QAction("계단식 배열(&C)", self)
        self._cascade_action.setIcon(self._icon_for("cascade"))
        self._cascade_action.triggered.connect(self._cascade_windows)

        self._tile_action = QAction("바둑판 배열(&T)", self)
        self._tile_action.setIcon(self._icon_for("tile"))
        self._tile_action.triggered.connect(self._tile_windows)

        self._vertical_action = QAction("수직 배열(&V)", self)
        self._vertical_action.triggered.connect(self._tile_vertical)

        self._horizontal_action = QAction("수평 배열(&H)", self)
        self._horizontal_action.triggered.connect(self._tile_horizontal)

        self._about_action = QAction("정보(&A)", self)
        self._about_action.triggered.connect(self._show_about)

        # 메뉴 순서: 파일, 편집, 창, 도움말
        file_menu = menubar.addMenu("파일(&F)")
        file_menu.addAction(self._new_action)
        file_menu.addAction(self._close_action)
        file_menu.addAction(self._close_all_action)

        file_menu.addSeparator()
        file_menu.addAction(self._quit_action)

        edit_menu = menubar.addMenu("편집(&E)")
        edit_menu.addAction(self._settings_action)

        window_menu = menubar.addMenu("창(&W)")
        window_menu.addAction(self._cascade_action)
        window_menu.addAction(self._tile_action)
        window_menu.addAction(self._vertical_action)
        window_menu.addAction(self._horizontal_action)

        help_menu = menubar.addMenu("도움말(&H)")
        help_menu.addAction(self._about_action)

        print("[LOG][_init_menu] 완료")

    def _icon_for(self, key: str) -> QIcon:
        root_dir = Path(__file__).resolve().parent.parent
        for relative_path in _ICON_CANDIDATES.get(key, []):
            image_path = root_dir / relative_path
            if image_path.exists():
                return QIcon(str(image_path))
        return QIcon()

    def _init_toolbar(self):
        print("[LOG][_init_toolbar] 호출")
        toolbar = QToolBar("주요 기능", self)
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        toolbar.addAction(self._new_action)
        toolbar.addAction(self._close_action)
        toolbar.addSeparator()
        toolbar.addAction(self._cascade_action)
        toolbar.addAction(self._tile_action)
        toolbar.addSeparator()
        toolbar.addAction(self._settings_action)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        print("[LOG][_init_toolbar] 완료")

    def _init_shortcuts(self):
        """단축키 등록 (CConEmuCtrl / GlobalHotkeys 대응)"""
        print("[LOG][_init_shortcuts] 호출")

        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(self.new_tab)
        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self._close_current_tab)
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(self.open_settings)

        for i in range(1, 10):
            QShortcut(QKeySequence(f"Alt+{i}"), self).activated.connect(
                lambda idx=i - 1: self._switch_tab(idx)
            )
        print("[LOG][_init_shortcuts] 완료 — Ctrl+T, Ctrl+W, Ctrl+,, Alt+1~9 등록됨")

    def _apply_settings(self):
        """AppSettings 값을 창 전체에 반영 (설정 변경 콜백)"""
        s = self._settings
        self.setWindowTitle(s.window_title)
        self.resize(s.window_width, s.window_height)
        if s.window_x >= 0 and s.window_y >= 0:
            self.move(s.window_x, s.window_y)
        if s.window_maximized:
            self.showMaximized()

        for view in self._tabs:
            view.apply_settings(s)
        print(
            f"[LOG][_apply_settings] 완료 — title={s.window_title!r}, "
            f"font={s.font_family}/{s.font_size}"
        )

    def open_settings(self):
        """설정 다이얼로그 열기 (Ctrl+, 또는 메뉴 → 편집 → 설정)"""
        print("[LOG][open_settings] 설정 다이얼로그 열기")
        dlg = SettingsDialog(self)
        dlg.exec()

    def _get_active_subwindow(self) -> _TerminalSubWindow | None:
        active = self.mdi_area.activeSubWindow()
        if isinstance(active, _TerminalSubWindow):
            return active
        return None

    def _subwindow_list(self) -> list[_TerminalSubWindow]:
        return [
            w for w in self.mdi_area.subWindowList(QMdiArea.WindowOrder.CreationOrder)
            if isinstance(w, _TerminalSubWindow)
        ]

    def _on_subwindow_closed(self, view: TerminalView, sub_window: _TerminalSubWindow):
        if view in self._tabs:
            self._tabs.remove(view)
        if sub_window in self._sub_windows:
            self._sub_windows.remove(sub_window)
        remaining = len(self._subwindow_list())
        self.status_bar.showMessage(f"콘솔 창 닫힘 (남은 창 {remaining})")
        print(f"[LOG][_on_subwindow_closed] 완료 — 남은 창 수={remaining}")
        if remaining == 0 and not self._is_shutting_down:
            print("[LOG][_on_subwindow_closed] 마지막 창 닫힘 — 앱 종료")
            self.close()

    def new_tab(self):
        """새 터미널 MDI 창 생성 (CConEmuMain::CreateVCon() 대응)"""
        print("[LOG][new_tab] 호출")
        view = TerminalView(self.mdi_area)
        view.title_changed.connect(self._on_tab_title_changed)
        view.process_exited.connect(self._on_process_exited)
        print(f"[LOG][new_tab] TerminalView 생성 완료: {view!r}")

        idx = len(self._tabs) + 1
        sub_window = _TerminalSubWindow(view, self._on_subwindow_closed, self.mdi_area)
        sub_window.setWindowTitle(f"터미널 {idx}")
        sub_window.resize(800, 480)

        self.mdi_area.addSubWindow(sub_window)
        self._tabs.append(view)
        self._sub_windows.append(sub_window)

        sub_window.show()
        self.mdi_area.setActiveSubWindow(sub_window)

        view.start()
        self.status_bar.showMessage(f"콘솔 창 {idx} 생성됨")
        print(f"[LOG][new_tab] 완료 — 콘솔 창 {idx} 활성")

    def close_tab(self, index: int):
        """지정 MDI 창 닫기"""
        windows = self._subwindow_list()
        print(f"[LOG][close_tab] 호출 — index={index}, 전체 창 수={len(windows)}")
        if not windows:
            return
        if 0 <= index < len(windows):
            windows[index].close()

    def _close_current_tab(self):
        sub_window = self._get_active_subwindow()
        print(f"[LOG][_close_current_tab] 현재 창={sub_window!r}")
        if sub_window is None:
            windows = self._subwindow_list()
            if windows:
                # 활성 창 정보가 없더라도 Ctrl+W 동작을 유지하기 위해 마지막 창을 닫음
                windows[-1].close()
            return
        sub_window.close()

    def _close_all_windows(self):
        print(f"[LOG][_close_all_windows] 호출 — 현재 창 수={len(self._subwindow_list())}")
        for sub_window in list(self._subwindow_list()):
            sub_window.close()

    def _switch_tab(self, index: int):
        windows = self._subwindow_list()
        print(f"[LOG][_switch_tab] 요청 index={index}, 전체 창 수={len(windows)}")
        if 0 <= index < len(windows):
            self.mdi_area.setActiveSubWindow(windows[index])
            print(f"[LOG][_switch_tab] 창 {index} 전환 완료")
        else:
            print(f"[LOG][_switch_tab] index={index} 범위 초과 — 무시")

    def _cascade_windows(self):
        print("[LOG][_cascade_windows] 호출")
        self.mdi_area.cascadeSubWindows()

    def _tile_windows(self):
        print("[LOG][_tile_windows] 호출")
        self.mdi_area.tileSubWindows()

    def _tile_vertical(self):
        windows = self._subwindow_list()
        count = len(windows)
        print(f"[LOG][_tile_vertical] 호출 — 창 수={count}")
        if count == 0:
            return
        rect = self.mdi_area.viewport().rect()
        if rect.width() < count * _MIN_VERTICAL_TILE_WIDTH:
            print("[LOG][_tile_vertical] 폭 부족으로 기본 바둑판 배열로 대체")
            self.mdi_area.tileSubWindows()
            return
        base_width = max(1, rect.width() // count)
        x = rect.x()
        for i, window in enumerate(windows):
            window.showNormal()
            width = base_width if i < count - 1 else rect.width() - base_width * (count - 1)
            window.setGeometry(x, rect.y(), width, rect.height())
            x += base_width

    def _tile_horizontal(self):
        windows = self._subwindow_list()
        count = len(windows)
        print(f"[LOG][_tile_horizontal] 호출 — 창 수={count}")
        if count == 0:
            return
        rect = self.mdi_area.viewport().rect()
        if rect.height() < count * _MIN_HORIZONTAL_TILE_HEIGHT:
            print("[LOG][_tile_horizontal] 높이 부족으로 기본 바둑판 배열로 대체")
            self.mdi_area.tileSubWindows()
            return
        base_height = max(1, rect.height() // count)
        y = rect.y()
        for i, window in enumerate(windows):
            window.showNormal()
            height = base_height if i < count - 1 else rect.height() - base_height * (count - 1)
            window.setGeometry(rect.x(), y, rect.width(), height)
            y += base_height

    def _find_subwindow_by_view(self, view: TerminalView) -> _TerminalSubWindow | None:
        for window in self._subwindow_list():
            if window.widget() is view:
                return window
        return None

    def _on_tab_title_changed(self, title: str):
        view = self.sender()
        if not isinstance(view, TerminalView):
            return
        sub_window = self._find_subwindow_by_view(view)
        print(f"[LOG][_on_tab_title_changed] 창 타이틀 변경: {title!r}")
        if sub_window is not None:
            sub_window.setWindowTitle(title[:24])

    def _on_process_exited(self):
        view = self.sender()
        if not isinstance(view, TerminalView):
            return
        sub_window = self._find_subwindow_by_view(view)
        print("[LOG][_on_process_exited] 창 프로세스 종료됨")
        if sub_window is not None:
            sub_window.setWindowTitle("[종료됨]")

    def _show_about(self):
        print("[LOG][_show_about] 정보 대화상자 표시")
        QMessageBox.about(
            self,
            "ConEmu-Py 정보",
            "ConEmu Python 변환 프로젝트\n\n"
            "원본: ConEmu (C++) by Maximus5\n"
            "Python 변환: MDI 프로토타입"
        )

    def closeEvent(self, event):
        print(f"[LOG][closeEvent] 앱 종료 요청 — 창 수={len(self._subwindow_list())}")
        self._is_shutting_down = True
        s = self._settings
        s.window_width = self.width()
        s.window_height = self.height()
        s.window_x = self.x()
        s.window_y = self.y()
        s.window_maximized = self.isMaximized()
        if s.save_on_exit:
            s.save()

        for sub_window in list(self._subwindow_list()):
            sub_window.close()

        for view in list(self._tabs):
            print(f"[LOG][closeEvent] 잔여 view.stop() 호출: {view!r}")
            view.stop()

        event.accept()
        print("[LOG][closeEvent] 완료")
