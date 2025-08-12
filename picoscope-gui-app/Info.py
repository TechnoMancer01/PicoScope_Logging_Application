import ctypes
from picosdk.ps3000a import ps3000a as ps
from picosdk.functions import assert_pico_ok

def get_picoscope_info():
    info = {}
    chandle = ctypes.c_int16()
    status = {}

    # Open the device
    status["openunit"] = ps.ps3000aOpenUnit(ctypes.byref(chandle), None)
    try:
        assert_pico_ok(status["openunit"])
    except Exception:
        powerStatus = status["openunit"]
        if powerStatus in (286, 282):  # PICO_POWER_SUPPLY_NOT_CONNECTED, PICO_USB3_0_DEVICE_NON_USB3_0_PORT
            status["changePowerSource"] = ps.ps3000aChangePowerSource(chandle, powerStatus)
            assert_pico_ok(status["changePowerSource"])
        else:
            raise

    # Helper to get info string
    def get_info(info_num):
        buffer = ctypes.create_string_buffer(256)
        required_size = ctypes.c_int16()
        ps.ps3000aGetUnitInfo(chandle, buffer, 256, ctypes.byref(required_size), info_num)
        return buffer.value.decode('utf-8').strip()

    # Get info fields
    info["Driver Version"] = get_info(0)
    info["USB Version"] = get_info(1)
    info["Hardware Version"] = get_info(2)
    info["Variant Info"] = get_info(3)
    info["Serial Number"] = get_info(4)
    info["Cal Date"] = get_info(5)
    info["Kernel Version"] = get_info(6)
    info["Digital Hardware Version"] = get_info(7)
    info["Analogue Hardware Version"] = get_info(8)
    info["Firmware 1"] = get_info(9)
    info["Firmware 2"] = get_info(10)

    # Close the device
    status["close"] = ps.ps3000aCloseUnit(chandle)
    assert_pico_ok(status["close"])

    return info

from picosdk.discover import find_unit

scope = find_unit()

print(scope.info)
scope.close()

if __name__ == "__main__":
    info = get_picoscope_info()
    print("PicoScope Device Information:")
    for k, v in info.items():
        print(f"{k}: {v}")