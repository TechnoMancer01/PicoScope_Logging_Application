import ctypes
import numpy as np
from picosdk.functions import adc2mV, assert_pico_ok
import time
import csv
import os
from PyQt5 import QtCore
import traceback

# Add the global signal for first sample recording
first_sample_recorded = None  # Global signal that GUI can connect to

class DataAcquisition:
    def __init__(self, driver):
        self.driver = driver
        self.chandle = ctypes.c_int16()
        self.status = {}
        self.is_recording = False  # Add recording state tracking
        self.bufferCompleteA = None
        self.bufferCompleteB = None
        self.bufferCompleteC = None
        self.bufferCompleteD = None
        self.totalSamples = 0
        self.nextSample = 0
        self.autoStopOuter = False
        self.wasCalledBack = False
        self.csvfile = None
        self.csvwriter = None
        self.csv_initialized = False
        self.maxADC = ctypes.c_int16(0)
        self.sample_interval = 0.25  # Default in ms
        self.sampleIntervalNs = 250 * 1000  # Default, will be updated
        self.time_unit = "ms"  # Default
        self.bufferDigital0 = None  # For D0-D7
        self.bufferDigital1 = None  # For D8-D15
        self.digital_channels = []
        # Fix voltage range storage - use actual constants instead of strings
        self.voltage_range = {
            "A": None,  # Will be set to actual range constant
            "B": None,
            "C": None,
            "D": None
        }
        self.voltage_offset = {
            "A": 0.0,
            "B": 0.0,
            "C": 0.0,
            "D": 0.0
        }
        self.voltage_max = {
            "A": None,
            "B": None,
            "C": None,
            "D": None
        }

    def set_voltage_range(self, channel, range_constant, offset=0.0):
        """Set the voltage range and offset for a channel.
        Example: set_voltage_range("A", driver.ps_2V, 0.0)
        """
        self.voltage_range[channel] = range_constant
        self.voltage_offset[channel] = offset

    def set_voltage_rail(self, channel, vmax):
        """Set the maximum voltage rail for a channel."""
        self.voltage_max[channel] = vmax

    def start_recording(self, sizeOfOneBuffer=10000, numBuffersToCapture=999999999, filename="acquisition.csv",
                        time_unit="ms", sample_interval=0.25, channels={"A": True, "B": False, "C": False, "D": False},
                        digital_channels=None):
        print("Started Recording")
        self.is_recording = True  # Set recording state
        self.time_unit = time_unit  # Store the selected unit
        self.sample_interval = sample_interval
        self.channels = channels
        
        # Filter digital channels based on driver capability
        if digital_channels and self._has_digital_channels():
            self.digital_channels = digital_channels
        else:
            if digital_channels:
                print("Warning: Digital channels requested but not supported by this scope model.")
            self.digital_channels = []
        
        self.totalSamples = sizeOfOneBuffer * numBuffersToCapture
        # For streaming mode, don't allocate large complete buffers - stream directly to CSV
        # Only small driver buffers are needed (allocated in setup_buffers)
        self.bufferCompleteA = None
        self.bufferCompleteB = None
        self.bufferCompleteC = None
        self.bufferCompleteD = None
        self.bufferDigital0 = None
        self.bufferDigital1 = None
        self.nextSample = 0
        self.autoStopOuter = False
        self.wasCalledBack = False
        self.csv_initialized = False

        # Open CSV file for writing
        header = [f'Time ({time_unit})']
        if channels.get("A", False):
            header.append('Channel A (mV)')
        if channels.get("B", False):
            header.append('Channel B (mV)')
        if channels.get("C", False):
            header.append('Channel C (mV)')
        if channels.get("D", False):
            header.append('Channel D (mV)')
        for dch in self.digital_channels:
            header.append(f'D{dch}')
        self.csvfile = open(filename, mode='w', newline='')
        print(f"Logging data to: {os.path.abspath(filename)}")
        self.csvwriter = csv.writer(self.csvfile)
        self.csvwriter.writerow(header)

        self.status["openunit"] = self.driver.psOpenUnit(ctypes.byref(self.chandle), None)
        try:
            assert_pico_ok(self.status["openunit"])
        except Exception:
            powerStatus = self.status["openunit"]
            # 286 = PICO_POWER_SUPPLY_NOT_CONNECTED, 282 = PICO_POWER_SUPPLY_UNDERVOLTAGE
            if powerStatus in (286, 282):
                self.status["changePowerSource"] = self.driver.psChangePowerSource(self.chandle, powerStatus)
                assert_pico_ok(self.status["changePowerSource"])
            else:
                raise

        # Set up channels and buffers
        self.setup_channels()
        self.setup_buffers(sizeOfOneBuffer)

        # Get maxADC value before streaming and check for errors
        self.status["maximumValue"] = self.driver.psMaximumValue(self.chandle, ctypes.byref(self.maxADC))
        assert_pico_ok(self.status["maximumValue"])

        # Begin streaming mode
        self.run_streaming(sizeOfOneBuffer)

    def setup_channels(self):
        # Use per-channel voltage range and offset
        for ch, pico_ch in zip("ABCD", [
            self.driver.ps_CHANNEL_A,
            self.driver.ps_CHANNEL_B,
            self.driver.ps_CHANNEL_C,
            self.driver.ps_CHANNEL_D
        ]):
            if self.channels.get(ch, False):
                # Convert voltage range string to actual constant if needed
                channel_range = self.voltage_range[ch]
                if channel_range is None:
                    channel_range = self.driver.ps_20V  # Default to 20V
                elif isinstance(channel_range, str):
                    # Convert string to actual range constant
                    channel_range = self._convert_range_string_to_constant(channel_range)
                analogue_offset = self.voltage_offset[ch]
            else:
                channel_range = self.driver.ps_20V
                analogue_offset = 0.0
            
            self.status[f"setCh{ch}"] = self.driver.psSetChannel(
                self.chandle,
                pico_ch,
                1 if self.channels.get(ch, False) else 0,
                self.driver.ps_DC,
                channel_range,
                analogue_offset)
            assert_pico_ok(self.status[f"setCh{ch}"])

    def _convert_range_string_to_constant(self, range_string):
        """Convert voltage range string to actual driver constant."""

        # For PS4000A, try to use the range directly from PICO_CONNECT_PROBE_RANGE
        if hasattr(self.driver, 'ps_RANGE') and hasattr(self.driver.ps_RANGE, 'get'):
            if range_string in self.driver.ps_RANGE:
                return self.driver.ps_RANGE[range_string]
        
        # Handle common voltage range patterns for both PS3000A and PS4000A
        range_mapping = {}
        
        # PS3000A standard ranges
        if hasattr(self.driver, 'ps_RANGE') and 'PS3000A_20V' in str(self.driver.ps_RANGE):
            range_mapping.update({
                "PS3000A_20V": self.driver.ps_RANGE.get("PS3000A_20V", self.driver.ps_20V),
                "PS3000A_2V": self.driver.ps_RANGE.get("PS3000A_2V", self.driver.ps_2V),
                "PS3000A_10V": self.driver.ps_RANGE.get("PS3000A_10V", 9),
                "PS3000A_5V": self.driver.ps_RANGE.get("PS3000A_5V", 8),
                "PS3000A_1V": self.driver.ps_RANGE.get("PS3000A_1V", 6),
                "PS3000A_500MV": self.driver.ps_RANGE.get("PS3000A_500MV", 5),
                "PS3000A_200MV": self.driver.ps_RANGE.get("PS3000A_200MV", 4),
                "PS3000A_100MV": self.driver.ps_RANGE.get("PS3000A_100MV", 3),
                "PS3000A_50MV": self.driver.ps_RANGE.get("PS3000A_50MV", 2),
                "PS3000A_20MV": self.driver.ps_RANGE.get("PS3000A_20MV", 1),
                "PS3000A_10MV": self.driver.ps_RANGE.get("PS3000A_10MV", 0),
            })
        
        # PS4000A X1 probe ranges (from #ps4000a.py attachment)
        if 'PS4000A' in str(type(self.driver).__name__):
            range_mapping.update({
                # X1 probe ranges
                "PICO_X1_PROBE_10MV": 0,
                "PICO_X1_PROBE_20MV": 1,
                "PICO_X1_PROBE_50MV": 2,
                "PICO_X1_PROBE_100MV": 3,
                "PICO_X1_PROBE_200MV": 4,
                "PICO_X1_PROBE_500MV": 5,
                "PICO_X1_PROBE_1V": 6,
                "PICO_X1_PROBE_2V": 7,
                "PICO_X1_PROBE_5V": 8,
                "PICO_X1_PROBE_10V": 9,
                "PICO_X1_PROBE_20V": 10,
                "PICO_X1_PROBE_50V": 11,
                "PICO_X1_PROBE_100V": 12,
                "PICO_X1_PROBE_200V": 13,
                
                # D9 BNC ranges
                "PICO_D9_BNC_10MV": 0,
                "PICO_D9_BNC_20MV": 1,
                "PICO_D9_BNC_50MV": 2,
                "PICO_D9_BNC_100MV": 3,
                "PICO_D9_BNC_200MV": 4,
                "PICO_D9_BNC_500MV": 5,
                "PICO_D9_BNC_1V": 6,
                "PICO_D9_BNC_2V": 7,
                "PICO_D9_BNC_5V": 8,
                "PICO_D9_BNC_10V": 9,
                "PICO_D9_BNC_20V": 10,
                "PICO_D9_BNC_50V": 11,
                "PICO_D9_BNC_100V": 12,
                "PICO_D9_BNC_200V": 13,
                
                # Differential ranges
                "PICO_DIFFERENTIAL_10MV": 0,
                "PICO_DIFFERENTIAL_20MV": 1,
                "PICO_DIFFERENTIAL_50MV": 2,
                "PICO_DIFFERENTIAL_100MV": 3,
                "PICO_DIFFERENTIAL_200MV": 4,
                "PICO_DIFFERENTIAL_500MV": 5,
                "PICO_DIFFERENTIAL_1V": 6,
                "PICO_DIFFERENTIAL_2V": 7,
                "PICO_DIFFERENTIAL_5V": 8,
                "PICO_DIFFERENTIAL_10V": 9,
                "PICO_DIFFERENTIAL_20V": 10,
                "PICO_DIFFERENTIAL_50V": 11,
                "PICO_DIFFERENTIAL_100V": 12,
                "PICO_DIFFERENTIAL_200V": 13,
                
                # 1kV probe ranges
                "PICO_1KV_2_5V": 6003,
                "PICO_1KV_5V": 6004,
                "PICO_1KV_12_5V": 6005,
                "PICO_1KV_25V": 6006,
                "PICO_1KV_50V": 6007,
                "PICO_1KV_125V": 6008,
                "PICO_1KV_250V": 6009,
                "PICO_1KV_500V": 6010,
                "PICO_1KV_1000V": 6011,
                
                # Common simple names
                "20V": 10,
                "2V": 7,
                "5V": 8,
                "10V": 9,
                "1V": 6,
            })
        
        # Use the mapping
        if range_string in range_mapping:
            return range_mapping[range_string]
        
        # Handle special cases - some GUI entries might be "MAX" ranges which should be ignored
        if "MAX" in range_string.upper():
            print(f"Info: Ignoring MAX range '{range_string}', using default 20V")
            return self.driver.ps_20V
        
        # Try to extract voltage from string (e.g., "5V" from "PICO_DIFFERENTIAL_5V")
        import re
        voltage_match = re.search(r'(\d+(?:\.\d+)?)\s*([MK]?)V', range_string, re.IGNORECASE)
        if voltage_match:
            voltage_value = float(voltage_match.group(1))
            unit = voltage_match.group(2).upper()
            
            if unit == 'M':  # millivolts
                voltage_value /= 1000
            elif unit == 'K':  # kilovolts
                voltage_value *= 1000
            
            # Map common voltage values to range constants
            voltage_to_range = {
                0.01: 0,   # 10mV
                0.02: 1,   # 20mV
                0.05: 2,   # 50mV
                0.1: 3,    # 100mV
                0.2: 4,    # 200mV
                0.5: 5,    # 500mV
                1.0: 6,    # 1V
                2.0: 7,    # 2V
                5.0: 8,    # 5V
                10.0: 9,   # 10V
                20.0: 10,  # 20V
                50.0: 11,  # 50V
                100.0: 12, # 100V
                200.0: 13, # 200V
            }
            
            if voltage_value in voltage_to_range:
                print(f"Info: Converted '{range_string}' to range constant {voltage_to_range[voltage_value]}")
                return voltage_to_range[voltage_value]
        
        # Fallback to 20V if unknown
        print(f"Warning: Unknown voltage range '{range_string}', defaulting to 20V")
        return self.driver.ps_20V

    def set_voltage_range(self, channel, range_value, offset=0.0):
        """Set the voltage range and offset for a channel.
        range_value can be either a string (e.g., "20V") or a numeric constant.
        """
        if isinstance(range_value, str):
            # Convert string to constant
            range_constant = self._convert_range_string_to_constant(range_value)
        else:
            # Assume it's already a numeric constant
            range_constant = range_value
        
        self.voltage_range[channel] = range_constant
        self.voltage_offset[channel] = offset

    def setup_buffers(self, sizeOfOneBuffer):
        memory_segment = 0
        # Get the correct ratio mode constant for each driver
        if hasattr(self.driver.ps_RATIO_MODE, 'get'):
            # PS3000A driver - use dictionary lookup
            ratio_mode_none = self.driver.ps_RATIO_MODE.get("PS3000A_RATIO_MODE_NONE", 0)
        else:
            # PS4000A driver - use direct value or fallback
            ratio_mode_none = getattr(self.driver, 'ps_RATIO_MODE_NONE', 0)

        # Setup analog channel buffers
        if self.channels.get("A", False):
            self.bufferAMax = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)
            self.status["setDataBuffersA"] = self.driver.psSetDataBuffers(self.chandle,
                self.driver.ps_CHANNEL_A,
                self.bufferAMax.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                None, sizeOfOneBuffer, memory_segment,
                ratio_mode_none)
            assert_pico_ok(self.status["setDataBuffersA"])
        if self.channels.get("B", False):
            self.bufferBMax = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)
            self.status["setDataBuffersB"] = self.driver.psSetDataBuffers(self.chandle,
                self.driver.ps_CHANNEL_B,
                self.bufferBMax.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                None, sizeOfOneBuffer, memory_segment,
                ratio_mode_none)
            assert_pico_ok(self.status["setDataBuffersB"])
        if self.channels.get("C", False):
            self.bufferCMax = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)
            self.status["setDataBuffersC"] = self.driver.psSetDataBuffers(self.chandle,
                self.driver.ps_CHANNEL_C,
                self.bufferCMax.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                None, sizeOfOneBuffer, memory_segment,
                ratio_mode_none)
            assert_pico_ok(self.status["setDataBuffersC"])
        if self.channels.get("D", False):
            self.bufferDMax = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)
            self.status["setDataBuffersD"] = self.driver.psSetDataBuffers(self.chandle,
                self.driver.ps_CHANNEL_D,
                self.bufferDMax.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                None, sizeOfOneBuffer, memory_segment,
                ratio_mode_none)
            assert_pico_ok(self.status["setDataBuffersD"])

        # Digital buffer setup - only for PS3000A series
        if self.digital_channels and self._has_digital_channels():
            try:
                self.bufferDigitalMax0 = np.zeros(shape=sizeOfOneBuffer, dtype=np.uint16)
                self.status["setDataBuffersDigital0"] = self.driver.psSetDataBuffers(
                    self.chandle,
                    self.driver.ps_DIGITAL_PORT0,  # Remove quotes - use direct constant
                    self.bufferDigitalMax0.ctypes.data_as(ctypes.POINTER(ctypes.c_uint16)),
                    None, sizeOfOneBuffer, memory_segment,
                    ratio_mode_none)
                assert_pico_ok(self.status["setDataBuffersDigital0"])
                
                self.bufferDigitalMax1 = np.zeros(shape=sizeOfOneBuffer, dtype=np.uint16)
                self.status["setDataBuffersDigital1"] = self.driver.psSetDataBuffers(
                    self.chandle,
                    self.driver.ps_DIGITAL_PORT1,  # Remove quotes - use direct constant
                    self.bufferDigitalMax1.ctypes.data_as(ctypes.POINTER(ctypes.c_uint16)),
                    None, sizeOfOneBuffer, memory_segment,
                    ratio_mode_none)
                assert_pico_ok(self.status["setDataBuffersDigital1"])
            except AttributeError:
                # Digital ports not available on this driver, disable digital channels
                print("Warning: Digital channels not available on this scope model. Disabling digital acquisition.")
                self.digital_channels = []

    def run_streaming(self, sizeOfOneBuffer):
        # Handle all four time units
        if self.time_unit == "s":
            sampleInterval = ctypes.c_int32(int(self.sample_interval * 1_000_000))  # s to us
            sampleUnits = self.driver.ps_US
            self.sampleIntervalNs = sampleInterval.value * 1000  # us to ns
        elif self.time_unit == "ms":
            sampleInterval = ctypes.c_int32(int(self.sample_interval * 1000))  # ms to us
            sampleUnits = self.driver.ps_US
            self.sampleIntervalNs = sampleInterval.value * 1000  # us to ns
        elif self.time_unit == "us":
            sampleInterval = ctypes.c_int32(int(self.sample_interval))  # us
            sampleUnits = self.driver.ps_US
            self.sampleIntervalNs = sampleInterval.value * 1000  # us to ns
        elif self.time_unit == "ns":
            sampleInterval = ctypes.c_int32(int(self.sample_interval))  # ns
            sampleUnits = self.driver.ps_NS
            self.sampleIntervalNs = sampleInterval.value  # already ns
        else:
            sampleInterval = ctypes.c_int32(int(self.sample_interval * 1000))
            sampleUnits = self.driver.ps_US
            self.sampleIntervalNs = sampleInterval.value * 1000

        maxPreTriggerSamples = 0
        autoStopOn = 1
        downsampleRatio = 1

        # Get the correct ratio mode constant for each driver
        if hasattr(self.driver.ps_RATIO_MODE, 'get'):
            # PS3000A driver - use dictionary lookup
            ratio_mode_none = self.driver.ps_RATIO_MODE.get("PS3000A_RATIO_MODE_NONE", 0)
        else:
            # PS4000A driver - use direct value or fallback
            ratio_mode_none = getattr(self.driver, 'ps_RATIO_MODE_NONE', 0)

        self.status["runStreaming"] = self.driver.psRunStreaming(
            self.chandle,
            ctypes.byref(sampleInterval),
            sampleUnits,
            maxPreTriggerSamples,
            self.totalSamples,
            autoStopOn,
            downsampleRatio,
            ratio_mode_none,
            sizeOfOneBuffer)
        assert_pico_ok(self.status["runStreaming"])

        # Convert the Python callback to a C function pointer
        self.cFuncPtr = self.driver.StreamingReadyType(self.streaming_callback)

        while self.nextSample < self.totalSamples and not self.autoStopOuter:
            self.wasCalledBack = False
            self.status["getStreamingLastestValues"] = self.driver.psGetStreamingLatestValues(
                self.chandle, self.cFuncPtr, None)
            if not self.wasCalledBack:
                time.sleep(0.01)

    # Add a signal for when first sample is recorded
    first_sample_recorded = None  # Global signal that GUI can connect to

    def streaming_callback(self, handle, noOfSamples, startIndex, overflow, triggerAt, triggered, autoStop, param):
        global first_sample_recorded
        
        self.wasCalledBack = True
        destEnd = self.nextSample + noOfSamples
        sourceEnd = startIndex + noOfSamples

        # Signal when the very first sample is recorded
        if self.nextSample == 0 and first_sample_recorded is not None:
            first_sample_recorded.emit()

        # Debug: Print callback information every 1000 samples
        if self.nextSample % 1000 == 0:
            print(f"Callback: samples {self.nextSample}-{destEnd}, received {noOfSamples} samples")

        if self.maxADC.value != 0:
            # Use the default 20V range for ADC conversion (this could be improved to use per-channel ranges)
            channel_range = self.driver.ps_20V
            
            # Stream directly from driver buffers - no large buffer copying needed
            sampleIntervalNs = self.sampleIntervalNs

            for i in range(noOfSamples):
                sample_index = startIndex + i
                
                if self.time_unit == "s":
                    t = (self.nextSample + i) * sampleIntervalNs / 1e9  # seconds
                elif self.time_unit == "ms":
                    t = (self.nextSample + i) * sampleIntervalNs / 1e6  # milliseconds
                elif self.time_unit == "us":
                    t = (self.nextSample + i) * sampleIntervalNs / 1e3  # microseconds
                elif self.time_unit == "ns":
                    t = (self.nextSample + i) * sampleIntervalNs  # nanoseconds
                else:
                    t = (self.nextSample + i) * sampleIntervalNs / 1e6  # default to milliseconds

                row = [t]
                # Read analog channel data directly from driver buffers
                if self.channels.get("A", False):
                    adc_val = self.bufferAMax[sample_index]
                    mv_val = self.adc_to_mv_single(adc_val, channel_range, self.maxADC)
                    row.append(mv_val)
                if self.channels.get("B", False):
                    adc_val = self.bufferBMax[sample_index]
                    mv_val = self.adc_to_mv_single(adc_val, channel_range, self.maxADC)
                    row.append(mv_val)
                if self.channels.get("C", False):
                    adc_val = self.bufferCMax[sample_index]
                    mv_val = self.adc_to_mv_single(adc_val, channel_range, self.maxADC)
                    row.append(mv_val)
                if self.channels.get("D", False):
                    adc_val = self.bufferDMax[sample_index]
                    mv_val = self.adc_to_mv_single(adc_val, channel_range, self.maxADC)
                    row.append(mv_val)
                # Read digital channel data directly from driver buffers
                if self.digital_channels:
                    digital_sample0 = self.bufferDigitalMax0[sample_index]
                    digital_sample1 = self.bufferDigitalMax1[sample_index]
                    for dch in self.digital_channels:
                        if dch < 8:
                            row.append((digital_sample0 >> dch) & 1)
                        else:
                            row.append((digital_sample1 >> (dch - 8)) & 1)
                
                # Write this sample's row immediately to CSV
                self.csvwriter.writerow(row)
                
                # Flush CSV file periodically
                if (self.nextSample + i) % 1000 == 0:
                    self.csvfile.flush()

        self.nextSample += noOfSamples
        if autoStop:
            self.autoStopOuter = True
            print("Auto-stop triggered by driver")

    def stop_recording(self):
        if not self.is_recording:
            print("No recording in progress")
            return
            
        print("Stopping Recording")
        try:
            self.status["stop"] = self.driver.psStop(self.chandle)
            assert_pico_ok(self.status["stop"])
            self.status["close"] = self.driver.psCloseUnit(self.chandle)
            assert_pico_ok(self.status["close"])
        except Exception as e:
            print(f"Error stopping recording: {e}")
        finally:
            self.is_recording = False  # Clear recording state
            # Close CSV file if open
            if self.csvfile:
                self.csvfile.close()
                self.csvfile = None
                self.csvwriter = None

    def adc_to_mv_single(self, adc_value, voltage_range_constant, maxADC):
        """Convert a single ADC count to millivolts."""
        # Voltage range mapping for both PS3000A and PS4000A
        voltage_ranges = {
            0: 0.01,    # 10mV
            1: 0.02,    # 20mV
            2: 0.05,    # 50mV
            3: 0.1,     # 100mV
            4: 0.2,     # 200mV
            5: 0.5,     # 500mV
            6: 1.0,     # 1V
            7: 2.0,     # 2V
            8: 5.0,     # 5V
            9: 10.0,    # 10V
            10: 20.0,   # 20V
            11: 50.0,   # 50V
            12: 100.0,  # 100V
            13: 200.0,  # 200V
        }
        
        # Get the voltage range in volts, default to 20V if unknown
        vRange = voltage_ranges.get(voltage_range_constant, 20.0)
        
        # Convert to millivolts: (ADC_value * voltage_range_in_volts * 1000) / max_ADC
        return (int(adc_value) * vRange * 1000.0) / maxADC.value

    def _has_digital_channels(self):
        """Check if the current driver supports digital channels."""
        # PS3000A has digital channels, PS4000A does not
        return hasattr(self.driver, 'ps_DIGITAL_PORT0') and hasattr(self.driver, 'ps_DIGITAL_PORT1')

# Singleton instance for GUI use, now initialized without a driver
_acquisition_instance = DataAcquisition(driver=None)

def start_recording(time_unit="ms", sample_interval=0.25, channels={"A": True, "B": True, "C": False, "D": False}, filename="acquisition.csv", digital_channels=None):
    if _acquisition_instance.driver is None:
        raise RuntimeError("Scope driver not set. Please select a scope at startup.")
    _acquisition_instance.start_recording(
        time_unit=time_unit,
        sample_interval=sample_interval,
        channels=channels,
        filename=filename,
        digital_channels=digital_channels
    )

def stop_recording():
    _acquisition_instance.stop_recording()

class AcquisitionThread(QtCore.QThread):
    def __init__(self, time_unit, sample_interval, channels, filename, digital_channels, voltage_rails=None, voltage_offsets=None):
        super().__init__()
        self.time_unit = time_unit
        self.sample_interval = sample_interval
        self.channels = channels
        self.filename = filename
        self.digital_channels = digital_channels
        self.voltage_rails = voltage_rails or {}
        self.voltage_offsets = voltage_offsets or {}

    def run(self):
        try:
            # Set voltage range and offset for each channel before starting acquisition
            for ch in self.voltage_rails:
                range_value = self.voltage_rails[ch]
                offset = self.voltage_offsets.get(ch, 0.0)
                # Pass the string value - it will be converted in set_voltage_range
                _acquisition_instance.set_voltage_range(ch, range_value, offset)
            
            # Add a 3.5-second startup delay to allow PicoScope to fully initialize
            print("Initializing PicoScope... Please wait 3.5 seconds")
            time.sleep(3.5)
            print("Starting data acquisition...")
            
            start_recording(
                time_unit=self.time_unit,
                sample_interval=self.sample_interval,
                channels=self.channels,
                filename=self.filename,
                digital_channels=self.digital_channels
            )
        except Exception:
            log_path = os.path.join(os.getcwd(), "picoscope_crash.log")
            with open(log_path, "a") as f:
                f.write("=== Crash Detected in AcquisitionThread ===\n")
                traceback.print_exc(file=f)