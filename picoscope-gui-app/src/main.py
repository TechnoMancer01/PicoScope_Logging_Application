from PyQt5.QtWidgets import QApplication
import sys
import os
import ctypes
import traceback

print("Starting PicoScope GUI Application...")

# Add picosdk to path when running as frozen executable
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    base_dir = os.path.dirname(sys.executable)
    picosdk_path = os.path.join(base_dir, 'picosdk')
    if os.path.exists(picosdk_path) and picosdk_path not in sys.path:
        sys.path.insert(0, os.path.dirname(picosdk_path))
else:
    # Running as script - use system-installed picosdk
    base_dir = os.path.dirname(os.path.abspath(__file__))

log_path = os.path.join(base_dir, "picoscope_crash.log")
csv_path = os.path.join(base_dir, "Data.csv")

def run_app():
    from gui import MainWindow, ScopeSelectDialog
    from scope_driver import PS3000ADriver, PS4000ADriver
    from data_acquisition import _acquisition_instance

    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        os.chdir(exe_dir)
        
        # Load DLLs from the executable directory
        dll_files = ['ps3000a.dll', 'ps4000a.dll']
        for dll_file in dll_files:
            dll_path = os.path.join(exe_dir, dll_file)
            if os.path.exists(dll_path):
                try:
                    ctypes.windll.LoadLibrary(dll_path)
                    print(f"Successfully loaded {dll_file}")
                except Exception as e:
                    print(f"Could not load {dll_file}: {e}")

    app = QApplication(sys.argv)

    # Scope selection dialog
    dlg = ScopeSelectDialog()
    if dlg.exec_() == 0:
        sys.exit(0)
    model_index = dlg.selected_model()
    if model_index == 0:
        driver = PS3000ADriver()
    else:
        driver = PS4000ADriver()

    # Set the driver for the singleton acquisition instance
    _acquisition_instance.driver = driver

    window = MainWindow(model_index)  # Pass the selected model index here
    window.show()
    sys.exit(app.exec_())

def excepthook(exc_type, exc_value, exc_tb):
    try:
        with open(log_path, "a") as f:
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

if __name__ == "__main__":
    run_app()