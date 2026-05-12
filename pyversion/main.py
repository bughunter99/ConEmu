"""
ConEmu Python 변환 - 1단계 진입점
CConEmuMain::WinMain() 대응
"""

import sys
from PySide6.QtWidgets import QApplication
from app import ConEmuApp
from gui.xp_style import apply_xp_style


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ConEmu-Py")
    app.setOrganizationName("ConEmu")
    apply_xp_style(app)

    window = ConEmuApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
