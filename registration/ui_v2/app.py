import sys
from PyQt6.QtWidgets import QApplication
from registration.ui.main_window import IDCardViewerMainWindow

def main():
    app = QApplication(sys.argv)
    window = IDCardViewerMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()