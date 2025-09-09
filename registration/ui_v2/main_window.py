from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent # Import QKeyEvent
from .nip_selector_widget import NIPSelectorWidget
from .display_widget import DisplayWidget
from .student_info_widget import StudentInfoWidget
from .card_options_widget import CardOptionsWidget
from .action_buttons_widget import ActionButtonsWidget
from .utils import show_qr, show_pdf_preview, load_data, generate_card
from registration.cardgenerator.cardgenerator import CardOptions
from pathlib import Path
from typing import Dict, Any
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QProgressDialog, QApplication
from PyQt6.QtCore import QTimer
import os
import subprocess

class IDCardViewerMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ID Card Viewer")
        self.setGeometry(100, 100, 800, 600) # Initial window size

        self.excel_file = 'database.xlsx'
        self.data, self.nips = load_data(self.excel_file)
        self.current_nip_index = 0
        self.card_options = CardOptions()

        # Create a central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create a main horizontal layout
        main_layout = QHBoxLayout(central_widget)

        # Left side: DisplayWidget
        self.display_widget = DisplayWidget()
        main_layout.addWidget(self.display_widget, 2)

        # Right side: Vertical layout for controls
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout, 1)

        # NIP Selector
        self.nip_selector_widget = NIPSelectorWidget(self)
        self.nip_selector_widget.set_nips(self.nips)
        right_layout.addWidget(self.nip_selector_widget)

        # Student Info Widget
        self.student_info_widget = StudentInfoWidget()
        right_layout.addWidget(self.student_info_widget)

        # Card Options Widget
        self.card_options_widget = CardOptionsWidget(self.card_options)
        right_layout.addWidget(self.card_options_widget)

        # Action Buttons Widget
        self.action_buttons_widget = ActionButtonsWidget()
        right_layout.addWidget(self.action_buttons_widget)

        right_layout.addStretch(1) # Add stretch to push widgets to the top

        # Connect signals to slots
        self.nip_selector_widget.nip_selected.connect(self.on_nip_selected)
        self.card_options_widget.card_options_changed.connect(self.on_card_option_changed)
        self.action_buttons_widget.generate_clicked.connect(self.generate_card_and_display)
        self.action_buttons_widget.reload_card_clicked.connect(self.reload_card)
        self.action_buttons_widget.reload_database_clicked.connect(self.reload_database)
        self.action_buttons_widget.open_card_clicked.connect(self.open_card)
        self.action_buttons_widget.print_card_clicked.connect(self.print_card)

        # Initial display update
        self.update_display(self.nips[self.current_nip_index])

    def on_nip_selected(self, nip: int):
        try:
            self.current_nip_index = self.nips.index(nip)
            self.update_display(nip)
        except (ValueError, KeyError) as e:
            print(f"Error: Could not find data for NIP '{nip}'. Details: {e}")

    def on_card_option_changed(self, name: str, value: str):
        setattr(self.card_options, name, value)
        print(f"Card option changed: {name} = {value}") # For debugging

    def update_display(self, nip: int):
        student_data = self.data[nip]
        self.student_info_widget.update_student_data(student_data)

        uuid = str(student_data['uuid'])
        pdf_path = Path("output_cards") / f"{nip}.pdf"

        # Update QR Code
        qr_image = show_qr(uuid)
        self.display_widget.set_qr_code_image(qr_image)

        # Update PDF Preview
        if not pdf_path.exists():
            template_path = Path("output_cards") / "template.pdf"
            if template_path.exists():
                pdf_image = show_pdf_preview(str(template_path))
            else:
                pdf_image = QPixmap()
                print(f"Template file {template_path} not found.")
        else:
            pdf_image = show_pdf_preview(str(pdf_path))
        
        self.display_widget.set_pdf_preview_image(pdf_image)

    def generate_card_and_display(self):
        current_nip = self.nips[self.current_nip_index]
        student_data = self.data[current_nip]

        progress_dialog = QProgressDialog("Generating ID card...", None, 0, 0, self)
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setCancelButton(None)
        progress_dialog.show()
        QApplication.processEvents() # Process events to show the dialog immediately

        try:
            generate_card(student_data, self.card_options)
            self.update_display(current_nip)
            print(f"Generated card for NIP: {current_nip}")
        except Exception as e:
            print(f"Error generating card: {e}")
        finally:
            progress_dialog.close()

    def reload_card(self):
        current_nip = self.nips[self.current_nip_index]
        self.update_display(current_nip)
        print(f"Reloaded card display for NIP: {current_nip}")

    def reload_database(self):
        self.data, self.nips = load_data(self.excel_file)
        self.nip_selector_widget.set_nips(self.nips)
        if self.nips:
            self.current_nip_index = 0
            self.update_display(self.nips[self.current_nip_index])
        else:
            print("No NIPs found in the database.")
        print("Database reloaded.")

    def open_card(self):
        current_nip = self.nips[self.current_nip_index]
        pdf_path = Path("output_cards") / f"{current_nip}.pdf"
        if pdf_path.exists():
            try:
                if os.name == 'nt': # For Windows
                    os.startfile(str(pdf_path))
                elif os.uname().sysname == 'Darwin': # For macOS
                    subprocess.run(['open', str(pdf_path)])
                else: # For Linux
                    subprocess.run(['xdg-open', str(pdf_path)])
                print(f"Opened card: {pdf_path}")
            except Exception as e:
                print(f"Error opening PDF: {e}")
        else:
            print(f"Card PDF not found for NIP: {current_nip}")

    def print_card(self):
        current_nip = self.nips[self.current_nip_index]
        pdf_path = Path("output_cards") / f"{current_nip}.pdf"
        if pdf_path.exists():
            try:
                # This is a placeholder. Actual printing would involve a more robust solution
                # like QPrintDialog or an external command with specific printer arguments.
                # For now, we'll just "open" it, assuming the user can print from there.
                if os.name == 'nt': # For Windows
                    os.startfile(str(pdf_path), "print")
                elif os.uname().sysname == 'Darwin': # For macOS
                    subprocess.run(['lp', str(pdf_path)]) # 'lp' is a common CUPS command
                else: # For Linux
                    subprocess.run(['lpr', str(pdf_path)]) # 'lpr' is a common CUPS command
                print(f"Sent card to printer: {pdf_path}")
            except Exception as e:
                print(f"Error printing PDF: {e}")
        else:
            print(f"Card PDF not found for NIP: {current_nip}")

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Left:
            self.prev_nip()
        elif event.key() == Qt.Key.Key_Right:
            self.next_nip()
        else:
            super().keyPressEvent(event)

    def prev_nip(self):
        if self.current_nip_index > 0:
            self.current_nip_index -= 1
            self.nip_selector_widget.set_current_nip(self.nips[self.current_nip_index])
            self.update_display(self.nips[self.current_nip_index])

    def next_nip(self):
        if self.current_nip_index < len(self.nips) - 1:
            self.current_nip_index += 1
            self.nip_selector_widget.set_current_nip(self.nips[self.current_nip_index])
            self.update_display(self.nips[self.current_nip_index])