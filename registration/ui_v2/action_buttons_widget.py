from PyQt6 import QtWidgets, QtCore

class ActionButtonsWidget(QtWidgets.QGroupBox):
    generate_clicked = QtCore.pyqtSignal()
    reload_card_clicked = QtCore.pyqtSignal()
    reload_database_clicked = QtCore.pyqtSignal()
    open_card_clicked = QtCore.pyqtSignal()
    print_card_clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Actions", parent)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.generate_button = QtWidgets.QPushButton("Generate")
        self.reload_card_button = QtWidgets.QPushButton("Reload Card")
        self.reload_database_button = QtWidgets.QPushButton("Reload Database")
        self.open_card_button = QtWidgets.QPushButton("Open Card")
        self.print_card_button = QtWidgets.QPushButton("Print Card")

        layout.addWidget(self.generate_button)
        layout.addWidget(self.reload_card_button)
        layout.addWidget(self.reload_database_button)
        layout.addWidget(self.open_card_button)
        layout.addWidget(self.print_card_button)

        self.generate_button.clicked.connect(self.generate_clicked.emit)
        self.reload_card_button.clicked.connect(self.reload_card_clicked.emit)
        self.reload_database_button.clicked.connect(self.reload_database_clicked.emit)
        self.open_card_button.clicked.connect(self.open_card_clicked.emit)
        self.print_card_button.clicked.connect(self.print_card_clicked.emit)
