# PicoScope GUI Application

This project is a comprehensive graphical user interface (GUI) application for controlling PicoScope data acquisition devices. It supports both PicoScope 3000 and 4000 series devices and allows users to record data from multiple channels with configurable voltage ranges, sample intervals, and output formats.

## Features

- **Multi-Device Support**: Compatible with PicoScope 3000 and 4000 series devices
- **Real-time Data Acquisition**: Streaming data acquisition with CSV output
- **Configurable Settings**: 
  - Sample intervals (s, ms, us, ns)
  - Voltage ranges per channel
  - DC offset adjustment
  - Digital channel recording (3000 series only)
- **Memory Optimized**: Efficient streaming approach for long-duration recordings
- **Cross-Platform**: Windows support with executable packaging

## Project Structure

```
picoscope-gui-app/
├── src/
│   ├── main.py                    # Application entry point with device selection
│   ├── gui.py                     # GUI layout, controls, and user interactions
│   ├── data_acquisition.py        # Core data acquisition and streaming logic
│   ├── scope_driver.py           # Device driver abstraction layer
│   ├── constants.py              # PicoScope status codes and constants
│   ├── library.py                # Low-level library interface
│   ├── ctypes_wrapper.py         # C library binding utilities
│   ├── ps3000a.py                # PicoScope 3000A series driver implementation
│   ├── ps4000a.py                # PicoScope 4000A series driver implementation
│   ├── memory_profiler.py        # Memory usage analysis tools
│   ├── runtime_memory_monitor.py # Runtime memory monitoring utilities
│   ├── storage_calculator.py     # Storage space calculation utilities
│   ├── utils.py                  # General utility functions
│   ├── device.py                 # Device management utilities
│   ├── discover.py               # Device discovery functionality
│   ├── errors.py                 # Error handling and definitions
│   ├── functions.py              # Common function definitions
│   ├── main.spec                 # PyInstaller specification for executable
│   └── *.dll                     # PicoScope driver DLLs
├── requirements.txt              # Python dependencies
└── README.md                     # Project documentation
```

## Installation

### Prerequisites
- Python 3.8 or higher
- PicoScope drivers installed on your system
- Compatible PicoScope device (3000 or 4000 series)

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd picoscope-gui-app
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure PicoScope drivers are installed:
   - Download and install PicoSDK from [Pico Technology website](https://www.picotech.com/downloads)

## Usage

### Running the Application

1. Start the application:
   ```bash
   python src/main.py
   ```

2. **Device Selection**: On startup, select your PicoScope model (3000 or 4000 series)

3. **Configuration**:
   - Set sample interval and time units
   - Choose CSV output filename
   - Select channels to record (A, B, C, D)
   - Configure voltage ranges for each channel
   - Set DC offset values if needed
   - Enable digital channels (3000 series only)

4. **Recording**:
   - Click "Start Recording" to begin data acquisition
   - Monitor elapsed time and initialization status
   - Click "Stop Recording" to end the session

### Output Format

Data is saved in CSV format with columns:
- Timestamp (in selected time units)
- Channel A voltage (mV)
- Channel B voltage (mV)
- Channel C voltage (mV)
- Channel D voltage (mV)
- Digital channels (if enabled)

## Building Executable

Create a standalone executable using PyInstaller:

```bash
cd src
pyinstaller main.spec
```

The executable will be created in the `dist/` directory.

## Memory Usage

This application is optimized for long-duration recordings:
- **Streaming Approach**: Data is written directly to CSV without large memory buffers
- **Memory Efficient**: ~50-100 MB total usage regardless of recording duration
- **Raspberry Pi Compatible**: Tested on various Pi models

## Dependencies

- **[PyQt5](https://pypi.org/project/PyQt5/)** - GUI framework
- **[numpy](https://numpy.org/)** - Numerical operations and data handling
- **[matplotlib](https://matplotlib.org/)** - Plotting capabilities (optional)
- **[picosdk](https://pypi.org/project/picosdk/)** - PicoScope device communication
- **[psutil](https://pypi.org/project/psutil/)** - System and memory monitoring

## Supported Devices

- **PicoScope 3000 Series**: Full support including digital channels
- **PicoScope 4000 Series**: Analog channels with advanced voltage ranges

## Performance

- **Sample Rates**: Up to device maximum (varies by model)
- **Recording Duration**: Unlimited (limited only by storage space)
- **Memory Usage**: Constant ~50-100 MB regardless of duration
- **File Output**: Direct CSV streaming for immediate data availability

## Troubleshooting

### Common Issues

1. **Driver Not Found**: Ensure PicoSDK is properly installed
2. **Device Not Detected**: Check USB connection and driver installation
3. **Memory Issues**: The application uses minimal memory; check system resources
4. **Permission Errors**: Run as administrator if needed for device access

### Log Files

- Application errors are logged to `picoscope_crash.log`
- Check console output for real-time status messages

## License

This project is licensed under the MIT License. See the LICENSE file for more details.