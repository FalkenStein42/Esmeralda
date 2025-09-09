from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox
from PyQt6.QtCore import pyqtSignal, Qt

class NIPSelectorWidget(QWidget):
    nip_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.comboBox = QComboBox(self)
        layout.addWidget(self.comboBox)
        self.setLayout(layout)
        self.comboBox.currentIndexChanged.connect(self._emit_nip_selected)

    def set_nips(self, nips):
        self.comboBox.clear()
        self.comboBox.addItem("Select NIP") # Placeholder or default
        # Store the actual NIPs (integers) and display their string representation
        self._nips_data = nips
        self.comboBox.addItems([str(nip) for nip in nips])

    def _emit_nip_selected(self, index):
        if index > 0: # Avoid emitting for the "Select NIP" placeholder
            selected_nip_str = self.comboBox.currentText()
            try:
                selected_nip_int = int(selected_nip_str)
                self.nip_selected.emit(selected_nip_int)
            except ValueError:
                print(f"Error: Could not convert selected NIP '{selected_nip_str}' to integer.")

    def set_current_nip(self, nip: int):
        try:
            # Find the index of the NIP in the stored data
            index = self._nips_data.index(nip)
            # Add 1 to account for the "Select NIP" placeholder at index 0
            self.comboBox.setCurrentIndex(index + 1)
        except ValueError:
            print(f"Error: NIP '{nip}' not found in the selector's data.")