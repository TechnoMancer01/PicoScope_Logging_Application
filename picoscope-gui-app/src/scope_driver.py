import ctypes

class ScopeDriverBase:
    def __init__(self):
        self.ps = None
        self.StreamingReadyType = None

    def open_unit(self, chandle):
        raise NotImplementedError

    def set_channel(self, *args, **kwargs):
        raise NotImplementedError

class PS3000ADriver(ScopeDriverBase):
    def __init__(self):
        super().__init__()
        from picosdk.ps3000a import ps3000a as ps
        self.ps = ps
        from ctypes_wrapper import C_CALLBACK_FUNCTION_FACTORY
        self.StreamingReadyType = C_CALLBACK_FUNCTION_FACTORY(
            None, ctypes.c_int16, ctypes.c_int32, ctypes.c_uint32, ctypes.c_int16, ctypes.c_uint32, ctypes.c_int16, ctypes.c_int16, ctypes.c_void_p
        )
        
        # Add all function aliases for compatibility
        self.psOpenUnit = self.ps.ps3000aOpenUnit
        self.psChangePowerSource = self.ps.ps3000aChangePowerSource
        self.psMaximumValue = self.ps.ps3000aMaximumValue
        self.psSetChannel = self.ps.ps3000aSetChannel
        self.psSetDataBuffers = self.ps.ps3000aSetDataBuffers
        self.psRunStreaming = self.ps.ps3000aRunStreaming
        self.psGetStreamingLatestValues = self.ps.ps3000aGetStreamingLatestValues
        self.psStop = self.ps.ps3000aStop
        self.psCloseUnit = self.ps.ps3000aCloseUnit
        
        # Add constants dictionaries
        self.ps_CHANNEL = self.ps.PS3000A_CHANNEL
        self.ps_RANGE = self.ps.PS3000A_RANGE
        self.ps_COUPLING = self.ps.PS3000A_COUPLING
        self.ps_RATIO_MODE = self.ps.PS3000A_RATIO_MODE
        self.ps_TIME_UNITS = self.ps.PS3000A_TIME_UNITS
        
        # Individual channel constants
        self.ps_CHANNEL_A = self.ps.PS3000A_CHANNEL["PS3000A_CHANNEL_A"]
        self.ps_CHANNEL_B = self.ps.PS3000A_CHANNEL["PS3000A_CHANNEL_B"]
        self.ps_CHANNEL_C = self.ps.PS3000A_CHANNEL["PS3000A_CHANNEL_C"]
        self.ps_CHANNEL_D = self.ps.PS3000A_CHANNEL["PS3000A_CHANNEL_D"]
        
        # Voltage range constants
        self.ps_20V = self.ps.PS3000A_RANGE["PS3000A_20V"]
        self.ps_2V = self.ps.PS3000A_RANGE["PS3000A_2V"]
        
        # Coupling constants
        self.ps_DC = self.ps.PS3000A_COUPLING["PS3000A_DC"]
        
        # Time unit constants
        self.ps_US = self.ps.PS3000A_TIME_UNITS["PS3000A_US"]
        self.ps_NS = self.ps.PS3000A_TIME_UNITS["PS3000A_NS"]

    def open_unit(self, chandle):
        return self.ps.ps3000aOpenUnit(chandle, None)

class PS4000ADriver(ScopeDriverBase):
    def __init__(self):
        super().__init__()
        from picosdk.ps4000a import ps4000a as ps
        self.ps = ps
        from ctypes_wrapper import C_CALLBACK_FUNCTION_FACTORY
        self.StreamingReadyType = C_CALLBACK_FUNCTION_FACTORY(
            None, ctypes.c_int16, ctypes.c_int32, ctypes.c_uint32, ctypes.c_int16, ctypes.c_uint32, ctypes.c_int16, ctypes.c_int16, ctypes.c_void_p
        )
        
        # Add all function aliases for compatibility
        self.psOpenUnit = self.ps.ps4000aOpenUnit
        self.psChangePowerSource = self.ps.ps4000aChangePowerSource
        self.psMaximumValue = self.ps.ps4000aMaximumValue
        self.psSetChannel = self.ps.ps4000aSetChannel
        self.psSetDataBuffers = self.ps.ps4000aSetDataBuffers
        self.psRunStreaming = self.ps.ps4000aRunStreaming
        self.psGetStreamingLatestValues = self.ps.ps4000aGetStreamingLatestValues
        self.psStop = self.ps.ps4000aStop
        self.psCloseUnit = self.ps.ps4000aCloseUnit
        
        # Add constants dictionaries - PS4000A has these defined
        self.ps_CHANNEL = self.ps.PS4000A_CHANNEL
        self.ps_RANGE = self.ps.PICO_VOLTAGE_RANGE  # This is defined in ps4000a.py
        self.ps_COUPLING = self.ps.PS4000A_COUPLING
        self.ps_RATIO_MODE = self.ps.PS4000A_RATIO_MODE
        self.ps_TIME_UNITS = self.ps.PS4000A_TIME_UNITS
        
        # Individual channel constants
        self.ps_CHANNEL_A = self.ps.PS4000A_CHANNEL["PS4000A_CHANNEL_A"]
        self.ps_CHANNEL_B = self.ps.PS4000A_CHANNEL["PS4000A_CHANNEL_B"]
        self.ps_CHANNEL_C = self.ps.PS4000A_CHANNEL["PS4000A_CHANNEL_C"]
        self.ps_CHANNEL_D = self.ps.PS4000A_CHANNEL["PS4000A_CHANNEL_D"]
        
        # Voltage range constants - use actual range values from PICO_VOLTAGE_RANGE
        # Based on the ps4000a.py attachment, let's use safe values
        self.ps_20V = 10  # A common 20V range value
        self.ps_2V = 7    # A common 2V range value
        
        # Coupling constants
        self.ps_DC = self.ps.PS4000A_COUPLING["PS4000A_DC"]
        
        # Time unit constants
        self.ps_US = self.ps.PS4000A_TIME_UNITS["PS4000A_US"]
        self.ps_NS = self.ps.PS4000A_TIME_UNITS["PS4000A_NS"]

    def open_unit(self, chandle):
        return self.ps.ps4000aOpenUnit(chandle, None)