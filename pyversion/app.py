"""
ConEmu Python 변환 - 메인 애플리케이션 창
CConEmuMain 클래스 대응 (1단계 프로토타입)
"""

import sys
print(f"[LOG][app.py] 모듈 로딩 시작 — Python {sys.version}")

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QPushButton, QMenuBar, QMenu, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QKeySequence, QIcon

from gui.terminal_view import TerminalView
from gui.settings_dialog import SettingsDialog, register_settings_changed
from config.settings import AppSettings
print("[LOG][app.py] 모듈 로딩 완료")


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
        print("[LOG][ConEmuApp.__init__] AppSettings 로드 완료")

        self._init_ui()
        self._init_menu()
        self._init_shortcuts()
        self._apply_settings()

        # 설정 변경 시 콜백 등록
        register_settings_changed(self._apply_settings)

        # 시작 시 탭 하나 자동 생성
        print("[LOG][ConEmuApp.__init__] 첫 번째 탭 자동 생성 시작")
        self.new_tab()
        print("[LOG][ConEmuApp.__init__] 초기화 완료")

    # ------------------------------------------------------------------
    # UI 초기화
    # ------------------------------------------------------------------

    def _init_ui(self):
        """창 레이아웃 초기화"""
        print("[LOG][_init_ui] 호출")
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
        print("[LOG][_init_ui] 완료 — QTabWidget, QStatusBar 생성됨")

    def _init_menu(self):
        """메뉴 바 초기화 (CConEmuMenu 대응)"""
        print("[LOG][_init_menu] 호출")
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

        # 설정 메뉴
        edit_menu = menubar.addMenu("편집(&E)")
        settings_action = QAction("설정(&S)…", self)
        settings_action.triggered.connect(self.open_settings)
        edit_menu.addAction(settings_action)

        print("[LOG][_init_menu] 완료")

    def _init_shortcuts(self):
        """단축키 등록 (CConEmuCtrl / GlobalHotkeys 대응)"""
        print("[LOG][_init_shortcuts] 호출")
        from PyQt6.QtGui import QShortcut

        # Ctrl+T: 새 탭
        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(self.new_tab)
        # Ctrl+W: 탭 닫기
        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self._close_current_tab)
        # Ctrl+,: 설정
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(self.open_settings)
        # Alt+1~9: 탭 전환
        for i in range(1, 10):
            QShortcut(QKeySequence(f"Alt+{i}"), self).activated.connect(
                lambda idx=i - 1: self._switch_tab(idx)
            )
        print("[LOG][_init_shortcuts] 완료 — Ctrl+T, Ctrl+W, Ctrl+,, Alt+1~9 등록됨")

    # ------------------------------------------------------------------
    # 설정 적용 / 설정 다이얼로그
    # ------------------------------------------------------------------

    def _apply_settings(self):
        """AppSettings 값을 창 전체에 반영 (설정 변경 콜백)"""
        s = self._settings
        self.setWindowTitle(s.window_title)
        self.resize(s.window_width, s.window_height)
        if s.window_x >= 0 and s.window_y >= 0:
            self.move(s.window_x, s.window_y)
        if s.window_maximized:
            self.showMaximized()
        # 탭 위치 적용
        from PyQt6.QtWidgets import QTabWidget
        pos_map = {
            "top":    QTabWidget.TabPosition.North,
            "bottom": QTabWidget.TabPosition.South,
        }
        self.tab_widget.setTabPosition(pos_map.get(s.tab_position, QTabWidget.TabPosition.North))
        # 각 탭의 TerminalView에 폰트/색상 갱신 요청
        for view in self._tabs:
            view.apply_settings(s)
        print(f"[LOG][_apply_settings] 완료 — title={s.window_title!r}, "
              f"font={s.font_family}/{s.font_size}, tab_pos={s.tab_position}")

    def open_settings(self):
        """설정 다이얼로그 열기 (Ctrl+, 또는 메뉴 → 편집 → 설정)"""
        print("[LOG][open_settings] 설정 다이얼로그 열기")
        dlg = SettingsDialog(self)
        dlg.exec()
        # SettingsDialog 내부에서 apply 시 _notify_settings_changed → _apply_settings 호출됨

    # ------------------------------------------------------------------
    # 탭 관리 (CVConGroup 대응)
    # ------------------------------------------------------------------

    def new_tab(self):
        """새 터미널 탭 생성 (CConEmuMain::CreateVCon() 대응)"""
        print("[LOG][new_tab] 호출")
        view = TerminalView(self)
        view.title_changed.connect(self._on_tab_title_changed)
        view.process_exited.connect(self._on_process_exited)
        print(f"[LOG][new_tab] TerminalView 생성 완료: {view!r}")

        idx = self.tab_widget.addTab(view, "터미널")
        self.tab_widget.setCurrentIndex(idx)
        self._tabs.append(view)
        print(f"[LOG][new_tab] 탭 추가 완료 — index={idx}, 전체 탭 수={self.tab_widget.count()}")
        view.start()
        self.status_bar.showMessage(f"탭 {idx + 1} 생성됨")
        print(f"[LOG][new_tab] 완료 — 탭 {idx + 1} 활성")

    def close_tab(self, index: int):
        """탭 닫기 (CVConGroup::CloseVCon() 대응)"""
        print(f"[LOG][close_tab] 호출 — index={index}, 전체 탭 수={self.tab_widget.count()}")
        if self.tab_widget.count() <= 1:
            print("[LOG][close_tab] 마지막 탭 — 앱 종료")
            self.close()
            return
        view = self.tab_widget.widget(index)
        if view:
            print(f"[LOG][close_tab] view.stop() 호출")
            view.stop()
            if view in self._tabs:
                self._tabs.remove(view)
        self.tab_widget.removeTab(index)
        print(f"[LOG][close_tab] 완료 — 남은 탭 수={self.tab_widget.count()}")

    def _close_current_tab(self):
        idx = self.tab_widget.currentIndex()
        print(f"[LOG][_close_current_tab] 현재 탭 index={idx}")
        self.close_tab(idx)

    def _switch_tab(self, index: int):
        print(f"[LOG][_switch_tab] 요청 index={index}, 전체 탭 수={self.tab_widget.count()}")
        if index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(index)
            print(f"[LOG][_switch_tab] 탭 {index} 전환 완료")
        else:
            print(f"[LOG][_switch_tab] index={index} 범위 초과 — 무시")

    # ------------------------------------------------------------------
    # 이벤트 핸들러
    # ------------------------------------------------------------------

    def _on_tab_title_changed(self, title: str):
        view = self.sender()
        idx = self.tab_widget.indexOf(view)
        print(f"[LOG][_on_tab_title_changed] 탭 {idx} 타이틀 변경: {title!r}")
        if idx >= 0:
            self.tab_widget.setTabText(idx, title[:24])

    def _on_process_exited(self):
        view = self.sender()
        idx = self.tab_widget.indexOf(view)
        print(f"[LOG][_on_process_exited] 탭 {idx}의 프로세스 종료됨")
        if idx >= 0:
            self.tab_widget.setTabText(idx, "[종료됨]")

    def _show_about(self):
        print("[LOG][_show_about] 정보 대화상자 표시")
        QMessageBox.about(
            self,
            "ConEmu-Py 정보",
            "ConEmu Python 변환 프로젝트\n\n"
            "원본: ConEmu (C++) by Maximus5\n"
            "Python 변환: 1단계 프로토타입"
        )

    def closeEvent(self, event):
        print(f"[LOG][closeEvent] 앱 종료 요청 — 탭 수={len(self._tabs)}")
        # 창 크기/위치 저장
        s = self._settings
        s.window_width = self.width()
        s.window_height = self.height()
        s.window_x = self.x()
        s.window_y = self.y()
        s.window_maximized = self.isMaximized()
        if s.save_on_exit:
            s.save()
        for view in list(self._tabs):
            print(f"[LOG][closeEvent] view.stop() 호출: {view!r}")
            view.stop()
        event.accept()
        print("[LOG][closeEvent] 완료")
