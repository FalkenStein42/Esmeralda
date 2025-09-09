from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

class DisplayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.qr_label = QLabel("QR Code will be displayed here")
        self.pdf_label = QLabel("PDF Preview will be displayed here")

        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pdf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.qr_label.setFixedSize(200, 200) # Assuming a fixed size for QR code
        self.pdf_label.setFixedSize(200, 200) # Assuming a fixed size for PDF preview

        layout = QVBoxLayout()
        layout.addWidget(self.qr_label)
        layout.addWidget(self.pdf_label)
        self.setLayout(layout)

    def set_qr_code_image(self, pixmap: QPixmap):
        self.qr_label.setPixmap(pixmap.scaled(self.qr_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def set_pdf_preview_image(self, pixmap: QPixmap):
        self.pdf_label.setPixmap(pixmap.scaled(self.pdf_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))