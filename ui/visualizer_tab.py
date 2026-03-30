from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QAbstractItemView, QHeaderView, QLabel, QHBoxLayout, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush

class VisualizerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._available_messages = {}
        self._build_ui()
        self.clear_grid()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = QLabel("CAN Frame Visualizer (64-bit Payload)")
        header.setObjectName("sectionTitle")
        layout.addWidget(header)

        # Info row
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("Select Message:"))
        self.message_combo = QComboBox()
        self.message_combo.setFixedWidth(200)
        self.message_combo.currentTextChanged.connect(self._on_message_selected)
        info_layout.addWidget(self.message_combo)

        self.signal_label = QLabel("Selected Signal: None")
        self.signal_label.setStyleSheet("color: #4A90E2; font-weight: bold; font-size: 14px;")
        info_layout.addWidget(self.signal_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # 8x8 Grid
        self.grid = QTableWidget(8, 8)
        self.grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.grid.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.grid.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.grid.verticalHeader().setVisible(True)
        self.grid.setVerticalHeaderLabels([f"Byte {i}" for i in range(8)])

        self.grid.horizontalHeader().setVisible(True)
        self.grid.setHorizontalHeaderLabels([f"Bit {i}" for i in range(7, -1, -1)])
        
        # Sizing
        self.grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.grid.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.grid.setMinimumHeight(400)

        # Initialize cells
        for r in range(8):
            for c in range(8):
                item = QTableWidgetItem("")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.grid.setItem(r, c, item)

        layout.addWidget(self.grid, 1)

    def clear_grid(self):
        for r in range(8):
            for c in range(8):
                item = self.grid.item(r, c)
                item.setText(str(r * 8 + (7 - c)))
                item.setBackground(QBrush(QColor("#FFFFFF")))
                item.setForeground(QBrush(QColor("#CBD5E1")))
                item.setToolTip("")

    def _get_bit_coords(self, bit_index):
        # bit_index is 0..63 mapped linearly per Byte
        byte_idx = bit_index // 8
        bit_within_byte = bit_index % 8
        col_idx = 7 - bit_within_byte # standard CAN visual layout puts bit 7 on left, bit 0 on right
        return byte_idx, col_idx

    def set_available_messages(self, messages_dict):
        """
        messages_dict: { "MessageName": [signal_dict, signal_dict...] }
        """
        self._available_messages = messages_dict
        self.message_combo.blockSignals(True)
        self.message_combo.clear()
        self.message_combo.addItems(list(messages_dict.keys()))
        self.message_combo.blockSignals(False)
        
        if self.message_combo.count() > 0:
            self._on_message_selected(self.message_combo.currentText())
        else:
            self.clear_grid()
            self.signal_label.setText("Selected Signal: None")

    def _on_message_selected(self, message_name):
        if not message_name or message_name not in self._available_messages:
            return
        signals = self._available_messages[message_name]
        self.update_visualizer(message_name, signals)

    def update_visualizer(self, message_name, signals, selected_signal_name=None):
        """
        signals: list of dicts with keys: 
           'Signal Name', 'Start Bit', 'Length', 'Byte Order'
        """
        self.clear_grid()
        
        idx = self.message_combo.findText(message_name)
        if idx >= 0:
            self.message_combo.blockSignals(True)
            self.message_combo.setCurrentIndex(idx)
            self.message_combo.blockSignals(False)
            
        self.signal_label.setText(f"Selected Signal: {selected_signal_name if selected_signal_name else 'None'}")

        if not message_name:
            return

        # Modern palette
        colors = ["#FEE2E2", "#FEF3C7", "#D1FAE5", "#E0E7FF", "#FCE7F3", "#F3E8FF", "#CCFBF1"]
        highlight_color = "#3B82F6"
        highlight_text = "#FFFFFF"

        color_idx = 0
        for sig in signals:
            name = sig.get('Signal Name', '')
            if not name:
                continue
                
            start_bit = sig.get('Start Bit')
            length = sig.get('Length')
            byte_order = str(sig.get('Byte Order', '')).lower()
            
            try:
                start_bit = int(start_bit)
                length = int(length)
            except:
                continue

            is_selected = (name == selected_signal_name)
            bg_color = QColor(highlight_color) if is_selected else QColor(colors[color_idx % len(colors)])
            fg_color = QColor(highlight_text) if is_selected else QColor("#1E293B")
            
            current_bit = start_bit
            is_motorola = "big" in byte_order

            for i in range(length):
                r, c = self._get_bit_coords(current_bit)
                if 0 <= r < 8 and 0 <= c < 8:
                    item = self.grid.item(r, c)
                    item.setBackground(QBrush(bg_color))
                    item.setForeground(QBrush(fg_color))
                    
                    # Truncate text to fit cell
                    display_text = name[:4] + ".." if len(name) > 6 else name
                    item.setText(display_text)
                    item.setToolTip(f"{name} (Bit {current_bit})")
                
                if is_motorola:
                    # Motorola MSB calculation layout (counts down, wraps back)
                    if current_bit % 8 == 0:
                        current_bit += 15
                    else:
                        current_bit -= 1
                else:
                    # Intel LSB layout mapping (counts up)
                    current_bit += 1

            color_idx += 1
