"""
ConEmu Python 변환 - 메인 애플리케이션 창
CConEmuMain 클래스 대응 (1단계 프로토타입)
"""

import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QPushButton, QMenuBar, QMenu, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QKeySequence, QIcon

from gui.terminal_view import TerminalView


class ConEmuApp(QMainWindow):
    """
    메인 애플리케이션 창.
    C++ CConEmuMain 클래스의 Python 대응.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ConEmu-Py")
        self.resize(900, 600)
        self._tabs: list[TerminalView] = []

        self._init_ui()
        self._init_menu()
        self._init_shortcuts()

        # 시작 시 탭 하나 자동 생성
        self.new_tab()

    # ------------------------------------------------------------------
    # UI 초기화
    # ------------------------------------------------------------------

    def _init_ui(self):
        """창 레이아웃 초기화"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 탭 바 (CTabBarClass 대응)
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        layout.addWidget(self.tab_widget)

        # 상태 바 (CStatus 대응)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("준비")

    def _init_menu(self):
        """메뉴 바 초기화 (CConEmuMenu 대응)"""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("파일(&F)")
        new_action = QAction("새 탭(&T)", self)
        new_action.triggered.connect(self.new_tab)
        file_menu.addAction(new_action)

        close_action = QAction("탭 닫기(&W)", self)
        close_action.triggered.connect(self._close_current_tab)
        file_menu.addAction(close_action)

        file_menu.addSeparator()

        quit_action = QAction("종료(&Q)", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = menubar.addMenu("도움말(&H)")
        about_action = QAction("정보(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_shortcuts(self):
        """단축키 등록 (CConEmuCtrl / GlobalHotkeys 대응)"""
        from PyQt6.QtGui import QShortcut

        # Ctrl+T: 새 탭
        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(self.new_tab)
        # Ctrl+W: 탭 닫기
        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self._close_current_tab)
        # Alt+1~9: 탭 전환
        for i in range(1, 10):
            QShortcut(QKeySequence(f"Alt+{i}"), self).activated.connect(
                lambda idx=i - 1: self._switch_tab(idx)
            )

    # ------------------------------------------------------------------
    # 탭 관리 (CVConGroup 대응)
    # ------------------------------------------------------------------

    def new_tab(self):
        """새 터미널 탭 생성 (CConEmuMain::CreateVCon() 대응)"""
        view = TerminalView(self)
        view.title_changed.connect(self._on_tab_title_changed)
        view.process_exited.connect(self._on_process_exited)

        idx = self.tab_widget.addTab(view, "터미널")
        self.tab_widget.setCurrentIndex(idx)
        self._tabs.append(view)
        view.start()
        self.status_bar.showMessage(f"탭 {idx + 1} 생성됨")

    def close_tab(self, index: int):
        """탭 닫기 (CVConGroup::CloseVCon() 대응)"""
        if self.tab_widget.count() <= 1:
            self.close()
            return
        view = self.tab_widget.widget(index)
        if view:
            view.stop()
            if view in self._tabs:
                self._tabs.remove(view)
        self.tab_widget.removeTab(index)

    def _close_current_tab(self):
        self.close_tab(self.tab_widget.currentIndex())

    def _switch_tab(self, index: int):
        if index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # 이벤트 핸들러
    # ------------------------------------------------------------------

    def _on_tab_title_changed(self, title: str):
        view = self.sender()
        idx = self.tab_widget.indexOf(view)
        if idx >= 0:
            self.tab_widget.setTabText(idx, title[:24])

    def _on_process_exited(self):
        view = self.sender()
        idx = self.tab_widget.indexOf(view)
        if idx >= 0:
            self.tab_widget.setTabText(idx, "[종료됨]")

    def _show_about(self):
        QMessageBox.about(
            self,
            "ConEmu-Py 정보",
            "ConEmu Python 변환 프로젝트\n\n"
            "원본: ConEmu (C++) by Maximus5\n"
            "Python 변환: 1단계 프로토타입"
        )

    def closeEvent(self, event):
        for view in list(self._tabs):
            view.stop()
        event.accept()
