import dataclasses
from typing import Literal, get_type_hints, get_args

from PyQt6 import QtWidgets, QtCore

from registration.cardgenerator.cardgenerator import CardOptions

class CardOptionsWidget(QtWidgets.QGroupBox):
    card_options_changed = QtCore.pyqtSignal(str, str)

    def __init__(self, card_options: CardOptions, parent=None):
        super().__init__("Card Options", parent)
        self.card_options = card_options
        self.option_button_groups = {}

        self._main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self._main_layout)
        self._create_dynamic_options()

    def _create_dynamic_options(self):
        type_hints = get_type_hints(CardOptions)
        for field in dataclasses.fields(CardOptions):
            field_name = field.name
            field_type_hints = type_hints.get(field_name)

            if field_type_hints is not None and hasattr(field_type_hints, '__origin__') and field_type_hints.__origin__ is Literal:
                options = get_args(field_type_hints)

                field_layout = QtWidgets.QHBoxLayout()
                field_layout.addWidget(QtWidgets.QLabel(f"{field_name.capitalize()}:"))

                button_group = QtWidgets.QButtonGroup(self)
                self.option_button_groups[field_name] = button_group

                current_value = getattr(self.card_options, field_name)

                for option in options:
                    radio_button = QtWidgets.QRadioButton(str(option))
                    radio_button.setProperty("field_name", field_name)
                    radio_button.setProperty("option_value", str(option))
                    button_group.addButton(radio_button)
                    field_layout.addWidget(radio_button)

                    if str(option) == str(current_value):
                        radio_button.setChecked(True)

                button_group.buttonClicked.connect(self._on_option_selected)
                self._main_layout.addLayout(field_layout)

    def _on_option_selected(self, button):
        field_name = button.property("field_name")
        new_value = button.property("option_value")
        setattr(self.card_options, field_name, new_value)
        self.card_options_changed.emit(field_name, new_value)
        print(f"Updated card option '{field_name}' to '{new_value}'")

    def get_card_options(self) -> CardOptions:
        return self.card_options