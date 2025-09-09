from PyQt6 import QtWidgets, QtCore
from typing import Dict, Any

class StudentInfoWidget(QtWidgets.QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Student Info", parent)
        self.layout = QtWidgets.QVBoxLayout(self)

        self.info_text_edit = QtWidgets.QTextEdit(self)
        self.info_text_edit.setReadOnly(True)
        self.info_text_edit.setDisabled(True)
        self.layout.addWidget(self.info_text_edit)

    def update_student_data(self, student_data: Dict[str, Any]):
        self.info_text_edit.setDisabled(False)
        self.info_text_edit.clear()
        for key, value in student_data.items():
            self.info_text_edit.append(f"{key}: {value}")
        self.info_text_edit.setDisabled(True)