from PyQt5 import QtWidgets, QtCore
import sys
import time
from data_acquisition import start_recording, stop_recording

class ScopeSelectDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select PicoScope Model")
        layout = QtWidgets.QVBoxLayout()
        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(["PicoScope 3000 Series", "PicoScope 4000 Series"])
        layout.addWidget(QtWidgets.QLabel("Select your PicoScope model:"))
        layout.addWidget(self.combo)
        btn = QtWidgets.QPushButton("OK")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
        self.setLayout(layout)

    def selected_model(self):
        return self.combo.currentIndex()  # 0 for 3000, 1 for 4000

class AcquisitionThread(QtCore.QThread):
    # Add a signal to communicate with the GUI
    countdown_update = QtCore.pyqtSignal(str)
    first_sample_signal = QtCore.pyqtSignal()  # Signal when first sample is actually recorded
    
    def __init__(self, time_unit, sample_interval, channels, filename, digital_channels, voltage_rails, voltage_offsets):
        super().__init__()
        self.time_unit = time_unit
        self.sample_interval = sample_interval
        self.channels = channels
        self.filename = filename
        self.digital_channels = digital_channels
        self.voltage_rails = voltage_rails
        self.voltage_offsets = voltage_offsets

    def run(self):
        from data_acquisition import _acquisition_instance, start_recording
        import data_acquisition
        
        # Connect the global signal to our thread signal
        data_acquisition.first_sample_recorded = self.first_sample_signal
        
        # Set voltage ranges
        for ch, range_name in self.voltage_rails.items():
            offset = self.voltage_offsets.get(ch, 0.0)
            _acquisition_instance.set_voltage_range(ch, range_name, offset)
        
        # Show initialization message
        self.countdown_update.emit("Initializing PicoScope...")
        
        # Start recording immediately
        start_recording(
            time_unit=self.time_unit,
            sample_interval=self.sample_interval,
            channels=self.channels,
            filename=self.filename,
            digital_channels=self.digital_channels
        )

class MainWindow(QtWidgets.QWidget):
    def __init__(self, model_index=0):
        super().__init__()
        self.model_index = model_index
        self.setWindowTitle(f"PicoScope GUI Application - {'3000 Series' if model_index == 0 else '4000 Series'}")
        self.setGeometry(100, 100, 400, 500)

        # Import the correct ps module based on model_index
        if self.model_index == 0:
            from picosdk.ps3000a import ps3000a as ps
        else:
            from picosdk.ps4000a import ps4000a as ps
        self.ps = ps

        self.time_unit_combo = QtWidgets.QComboBox(self)
        self.time_unit_combo.addItems(["s", "ms", "us", "ns"])

        self.interval_input = QtWidgets.QLineEdit(self)
        self.interval_input.setPlaceholderText("Enter sample interval (e.g. 0.5)")

        self.filename_input = QtWidgets.QLineEdit(self)
        self.filename_input.setPlaceholderText("Enter CSV filename (e.g. data.csv)")

        # Channel checkboxes
        self.channel_a_checkbox = QtWidgets.QCheckBox("Channel A", self)
        self.channel_a_checkbox.setChecked(True)
        self.channel_b_checkbox = QtWidgets.QCheckBox("Channel B", self)
        self.channel_b_checkbox.setChecked(False)
        self.channel_c_checkbox = QtWidgets.QCheckBox("Channel C", self)
        self.channel_c_checkbox.setChecked(False)
        self.channel_d_checkbox = QtWidgets.QCheckBox("Channel D", self)
        self.channel_d_checkbox.setChecked(False)

        # Voltage rails dropdowns for each channel
        self.rail_inputs = {}
        self.offset_inputs = {}
        # Use the correct range enum for the selected series
        if self.model_index == 0:  # PS3000A
            voltage_range_enum = self.ps.PS3000A_RANGE
            # Remove the MAX_RANGES entry
            max_range_key = next((k for k in voltage_range_enum.keys() if "MAX" in k), None)
            if max_range_key:
                voltage_range_names = [k for k in voltage_range_enum.keys() if k != max_range_key]
            else:
                voltage_range_names = list(voltage_range_enum.keys())
        else:  # PS4000A
            voltage_range_enum = self.ps.PICO_CONNECT_PROBE_RANGE
            # Filter out invalid ranges for PS4000A
            voltage_range_names = []
            for k in voltage_range_enum.keys():
                # Skip MAX ranges and invalid entries
                if "MAX" in k.upper():
                    continue
                # Skip ranges that don't contain voltage information
                if not any(unit in k.upper() for unit in ['MV', 'V']):
                    continue
                # Skip current clamp ranges for now (they use different units)
                if "CURRENT_CLAMP" in k.upper():
                    continue
                # Only include reasonable voltage ranges
                if any(probe in k.upper() for probe in ['X1_PROBE', 'D9_BNC', 'DIFFERENTIAL', '1KV']):
                    voltage_range_names.append(k)
        
        for ch in "ABCD":
            rail_combo = QtWidgets.QComboBox(self)
            rail_combo.addItems(voltage_range_names)
            # Set a reasonable default (try to find 5V or 20V)
            default_range = None
            for name in voltage_range_names:
                if "5V" in name and "50V" not in name and "500MV" not in name:
                    default_range = name
                    break
            if not default_range:
                for name in voltage_range_names:
                    if "20V" in name and "200V" not in name:
                        default_range = name
                        break
            if default_range:
                rail_combo.setCurrentText(default_range)
            else:
                rail_combo.setCurrentIndex(0)  # Use first available
            self.rail_inputs[ch] = rail_combo

            offset_spin = QtWidgets.QDoubleSpinBox(self)
            offset_spin.setRange(-20.0, 20.0)
            offset_spin.setSingleStep(0.01)
            offset_spin.setDecimals(3)
            offset_spin.setValue(0.0)
            self.offset_inputs[ch] = offset_spin

        # Digital channel checkboxes D0-D15 (only for PS3000A)
        self.digital_checkboxes = []
        self.digital_layout = QtWidgets.QHBoxLayout()
        
        if self.model_index == 0:  # PS3000A - show digital channels
            self.digital_layout.addWidget(QtWidgets.QLabel("Digital Channels:"))
            for i in range(16):
                cb = QtWidgets.QCheckBox(f"D{i}", self)
                cb.setChecked(False)
                self.digital_checkboxes.append(cb)
                self.digital_layout.addWidget(cb)
        else:  # PS4000A - hide digital channels completely
            pass

        self.timer_label = QtWidgets.QLabel("Elapsed Time: 00:00.000", self)
        self.initialization_label = QtWidgets.QLabel("", self)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.timer.setInterval(50)
        self.start_time = None
        self.recording_start_time = None

        self.start_button = QtWidgets.QPushButton("Start Recording", self)
        self.start_button.clicked.connect(self.start_recording)

        self.stop_button = QtWidgets.QPushButton("Stop Recording", self)
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setEnabled(False)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Sample interval:"))
        layout.addWidget(self.interval_input)
        layout.addWidget(QtWidgets.QLabel("Time unit:"))
        layout.addWidget(self.time_unit_combo)
        layout.addWidget(QtWidgets.QLabel("CSV filename:"))
        layout.addWidget(self.filename_input)
        layout.addWidget(QtWidgets.QLabel("Select channels to record:"))
        channel_layout = QtWidgets.QHBoxLayout()
        channel_layout.addWidget(self.channel_a_checkbox)
        channel_layout.addWidget(self.channel_b_checkbox)
        channel_layout.addWidget(self.channel_c_checkbox)
        channel_layout.addWidget(self.channel_d_checkbox)
        layout.addLayout(channel_layout)

        rails_layout = QtWidgets.QFormLayout()
        for ch in "ABCD":
            rails_layout.addRow(f"{ch} Voltage Range:", self.rail_inputs[ch])
            rails_layout.addRow(f"{ch} DC Offset:", self.offset_inputs[ch])
        layout.addLayout(rails_layout)

        # Only add digital layout if we have digital channels (PS3000A)
        if self.model_index == 0:
            layout.addWidget(QtWidgets.QLabel("Select digital channels to record:"))
        layout.addLayout(self.digital_layout)
        
        layout.addWidget(self.initialization_label)
        layout.addWidget(self.timer_label)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        self.setLayout(layout)
        self.acq_thread = None

    def start_recording(self):
        time_unit = self.time_unit_combo.currentText()
        try:
            sample_interval = float(self.interval_input.text())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for the sample interval.")
            return
        filename = self.filename_input.text().strip()
        if not filename:
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Select CSV file", "", "CSV Files (*.csv)")
            if not filename:
                QtWidgets.QMessageBox.warning(self, "No filename", "You must enter a CSV filename before recording.")
                return
            self.filename_input.setText(filename)
        channels = {
            "A": self.channel_a_checkbox.isChecked(),
            "B": self.channel_b_checkbox.isChecked(),
            "C": self.channel_c_checkbox.isChecked(),
            "D": self.channel_d_checkbox.isChecked()
        }
        
        # Only get digital channels for PS3000A
        if self.model_index == 0:  # PS3000A
            digital_channels = [i for i, cb in enumerate(self.digital_checkboxes) if cb.isChecked()]
        else:  # PS4000A
            digital_channels = None  # No digital channels for PS4000A

        voltage_rails = {ch: self.rail_inputs[ch].currentText() for ch in "ABCD"}
        voltage_offsets = {ch: self.offset_inputs[ch].value() for ch in "ABCD"}

        self.acq_thread = AcquisitionThread(
            time_unit, sample_interval, channels, filename, digital_channels,
            voltage_rails=voltage_rails, voltage_offsets=voltage_offsets
        )
        
        # Connect signals
        self.acq_thread.countdown_update.connect(self.update_initialization_status)
        self.acq_thread.first_sample_signal.connect(self.on_first_sample_recorded)
        
        # Don't start timer yet - wait for first sample
        self.start_time = None
        self.recording_start_time = None
        
        self.acq_thread.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
    def update_initialization_status(self, message):
        self.initialization_label.setText(message)
    
    def on_first_sample_recorded(self):
        """Called when the first sample is actually recorded by the PicoScope."""
        print("First sample recorded - starting timer")
        self.recording_start_time = QtCore.QTime.currentTime()
        self.timer.start()
        self.initialization_label.setText("Recording in progress...")

    def stop_recording(self):
        stop_recording()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.timer.stop()
        self.initialization_label.setText("")

    def update_timer(self):
        if self.recording_start_time is not None:
            # Show time since first sample was recorded
            elapsed = self.recording_start_time.msecsTo(QtCore.QTime.currentTime())
            minutes = (elapsed // 60000) % 60
            seconds = (elapsed // 1000) % 60
            milliseconds = elapsed % 1000
            self.timer_label.setText(f"Elapsed Time: {minutes:02}:{seconds:02}.{milliseconds:03}")

def main(model_index=0):
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(model_index=model_index)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()