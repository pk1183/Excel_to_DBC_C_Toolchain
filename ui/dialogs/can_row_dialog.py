import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, 
    QPushButton, QHBoxLayout, QMessageBox, QGroupBox
)
from PyQt6.QtGui import QIntValidator, QDoubleValidator
from PyQt6.QtCore import Qt, QObject, QEvent, pyqtSignal
from PyQt6.QtWidgets import QCompleter

class CanRowDialog(QDialog):
    save_requested = pyqtSignal(dict, bool, int)

    def __init__(self, parent=None, existing_messages=None, existing_signals=None, edit_data=None, update_row=-1):
        """
        existing_messages: dict pairing message names to their data e.g. 
            {"EngineStatus": {"Message ID": "0x100", "ID Type": "Standard", "Cycle Time": "100"}}
        existing_signals: list of all existing signal names to prevent duplicates
        """
        super().__init__(parent)
        self.existing_messages = existing_messages or {}
        self.existing_signals = existing_signals or []
        self.edit_data = edit_data or {}
        self.is_update = bool(edit_data)
        self.update_row = update_row
        
        self.setWindowTitle("Edit CAN Matrix Row" if self.is_update else "Add CAN Matrix Row")
        self.setMinimumWidth(450)
        self.init_ui()

    def _populate_combo(self, combo: QComboBox, items, current_value=None):
        combo.clear()
        items = [str(x).strip() for x in (items or []) if str(x).strip()]

        # Make combo typeable with autocomplete + validation
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)

        combo.setMaxVisibleItems(5)
        combo._last_valid_index = -1

        def find_matches(text: str) -> list[int]:
            t = text.strip().lower()
            if not t:
                return []
            return [i for i in range(combo.count())
                    if t in combo.itemText(i).lower()]

        def select_index(idx: int):
            if 0 <= idx < combo.count():
                combo.setCurrentIndex(idx)
                combo._last_valid_index = idx
                if combo.lineEdit():
                    combo.lineEdit().setText(combo.currentText())

        def validate_or_revert():
            text = combo.currentText().strip()
            # Allow custom string if it's not in the list (since we can create new messages)
            exact_idx = combo.findText(text, Qt.MatchFlag.MatchFixedString)
            if exact_idx >= 0:
                select_index(exact_idx)
            else:
                # If it's a new message, just accept it
                pass

        combo.lineEdit().returnPressed.connect(validate_or_revert)
        combo.lineEdit().editingFinished.connect(validate_or_revert)

        class _FocusGuard(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.FocusOut:
                    validate_or_revert()
                return False
        
        guard = _FocusGuard(combo)
        combo.lineEdit().installEventFilter(guard)
        combo._focus_guard = guard

        combo.currentIndexChanged.connect(lambda idx: setattr(combo, "_last_valid_index", idx))

        if items:
            combo.addItems(items)
        if current_value:
            idx = combo.findText(current_value)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.setCurrentText(current_value)
        else:
            combo.setCurrentText("")

    def init_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        # --- Message Section ---
        msg_group = QGroupBox("Message Information")
        msg_layout = QFormLayout(msg_group)

        self.msg_name = QComboBox()
        self._populate_combo(self.msg_name, list(self.existing_messages.keys()), current_value=self.edit_data.get("Message Name"))
        self.msg_name.currentTextChanged.connect(self._on_message_changed)
        msg_layout.addRow("Message Name *:", self.msg_name)

        self.msg_id = QLineEdit(str(self.edit_data.get("Message ID", "")))
        self.msg_id.setPlaceholderText("e.g. 0x100 or 256")
        self.msg_id.textEdited.connect(lambda text: self.msg_id.setText(text.upper()))
        msg_layout.addRow("Message ID *:", self.msg_id)

        self.id_type = QComboBox()
        self.id_type.addItems(["Standard", "Extended"])
        if "ID Type" in self.edit_data:
            self.id_type.setCurrentText(str(self.edit_data["ID Type"]).strip())
        msg_layout.addRow("ID Type:", self.id_type)

        self.cycle_time = QLineEdit(str(self.edit_data.get("Cycle Time", "")))
        self.cycle_time.setValidator(QIntValidator(0, 100000))
        self.cycle_time.setPlaceholderText("in ms")
        msg_layout.addRow("Cycle Time:", self.cycle_time)

        layout.addWidget(msg_group)

        # --- Signal Section ---
        sig_group = QGroupBox("Signal Information")
        sig_layout = QFormLayout(sig_group)

        self.sig_name = QLineEdit(str(self.edit_data.get("Signal Name", "")))
        sig_layout.addRow("Signal Name *:", self.sig_name)

        self.start_bit = QLineEdit(str(self.edit_data.get("Start Bit", "")))
        self.start_bit.setValidator(QIntValidator(0, 63))
        sig_layout.addRow("Start Bit *:", self.start_bit)

        self.length = QLineEdit(str(self.edit_data.get("Length", "")))
        self.length.setValidator(QIntValidator(1, 64))
        sig_layout.addRow("Length *:", self.length)

        self.byte_order = QComboBox()
        self.byte_order.addItems(["Little Endian", "Big Endian"])
        if "Byte Order" in self.edit_data:
            self.byte_order.setCurrentText(str(self.edit_data["Byte Order"]).strip())
        sig_layout.addRow("Byte Order:", self.byte_order)

        self.factor = QLineEdit(str(self.edit_data.get("Factor", "1.0")))
        sig_layout.addRow("Factor:", self.factor)

        self.offset = QLineEdit(str(self.edit_data.get("Offset", "0.0")))
        sig_layout.addRow("Offset:", self.offset)

        self.min_val = QLineEdit(str(self.edit_data.get("Min", "0.0")))
        sig_layout.addRow("Minimum:", self.min_val)

        self.max_val = QLineEdit(str(self.edit_data.get("Max", "0.0")))
        sig_layout.addRow("Maximum:", self.max_val)

        self.unit = QLineEdit(str(self.edit_data.get("Unit", "")))
        sig_layout.addRow("Unit:", self.unit)

        self.value_desc = QLineEdit(str(self.edit_data.get("Value Descriptions", "")))
        self.value_desc.setPlaceholderText("e.g. 0:Off, 1:On")
        sig_layout.addRow("Value Descriptions:", self.value_desc)

        layout.addWidget(sig_group)

        # Footer
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save to Excel")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self.on_save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)

        layout.addLayout(buttons)
        self.setLayout(layout)

    def _on_message_changed(self, text):
        text = text.strip()
        if text in self.existing_messages:
            data = self.existing_messages[text]
            self.msg_id.setText(str(data.get("Message ID", "")))
            
            id_type_val = str(data.get("ID Type", "")).strip().lower()
            if "extended" in id_type_val or "29" in id_type_val:
                self.id_type.setCurrentText("Extended")
            elif "standard" in id_type_val:
                self.id_type.setCurrentText("Standard")

            self.cycle_time.setText(str(data.get("Cycle Time", "")))

    def validate_inputs(self):
        msg_name = self.msg_name.currentText().strip()
        msg_id = self.msg_id.text().strip()
        sig_name = self.sig_name.text().strip()
        start = self.start_bit.text().strip()
        length = self.length.text().strip()

        if not msg_name or not msg_id or not sig_name or not start or not length:
            QMessageBox.warning(self, "Validation Error", "Please fill in all required fields (*).")
            return False

        if " " in sig_name:
            QMessageBox.warning(self, "Validation Error", "Signal Name cannot contain spaces.")
            return False

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", sig_name):
            QMessageBox.warning(self, "Validation Error", "Signal Name must be alphanumeric and start with a letter or underscore.")
            return False

        if sig_name in self.existing_signals:
            if not (self.is_update and sig_name == self.edit_data.get("Signal Name")):
                QMessageBox.warning(self, "Validation Error", f"Signal Name '{sig_name}' already exists in this sheet. Please use a unique name.")
                return False

        return True

    def on_save(self):
        if not self.validate_inputs():
            return

        data = {
            "Message Name": self.msg_name.currentText().strip(),
            "Message ID": self.msg_id.text().strip(),
            "ID Type": self.id_type.currentText().strip(),
            "Cycle Time": self.cycle_time.text().strip(),
            "Signal Name": self.sig_name.text().strip(),
            "Start Bit": self.start_bit.text().strip(),
            "Length": self.length.text().strip(),
            "Byte Order": self.byte_order.currentText().strip(),
            "Factor": self.factor.text().strip(),
            "Offset": self.offset.text().strip(),
            "Min": self.min_val.text().strip(),
            "Max": self.max_val.text().strip(),
            "Unit": self.unit.text().strip(),
            "Value Descriptions": self.value_desc.text().strip(),
        }

        self.save_requested.emit(data, self.is_update, self.update_row)
        self.accept()
