import d2d_toolset as d2d

class CommandError(Exception):
    """制御コマンドの返答がNGの時を表すエラー"""
    pass

class VG01:
    UART_DELIMITER_RX = d2d.ASCII.CR #b'\x0D' # CR
    UART_DELIMITER_TX = d2d.ASCII.CR #b'\x0D' # CR

    CHANNELS = 4
    CH_CODES = ['A', 'B', 'C', 'D']

    RESULT_LEN = 2
    COMMAND_ERROR = b'NG'
    COMMAND_HANDLED = b'OK'

    WAVE_MAX_LENGTH = 4000
    UNIT_MV = 16
    DAC_MIN = 0
    DAC_MAX = 255

    USB_BUFFER_SIZE = 512

    ADDR_PARAMS_START = 16

    def __init__(self, ser, echo=False):
        self.ser = ser
        self.echo = echo

        self.read_params()
        pass

    def read_all(self):
        if self.ser.in_waiting:
            return self.ser.read(size=self.ser.in_waiting)
        return ""

    def _result_of(self, ret):
        return ret[-self.RESULT_LEN-len(self.UART_DELIMITER_RX):-len(self.UART_DELIMITER_RX)]

    def _data_of(self, ret):
        return ret[:-self.RESULT_LEN-len(self.UART_DELIMITER_RX)]

    def write(self, cmd):
        cmd += d2d.bytes_to_str(self.UART_DELIMITER_TX)#self.UART_DELIMITER_TX.decode()
        if self.echo:
            print(cmd)
            pass
        self.ser.write(d2d.str_to_bytes(cmd))#cmd.encode('UTF-8'))
        pass

    def write_raw(self, cmd):
        if self.echo:
            print(cmd)
            pass
        self.ser.write(d2d.str_to_bytes(cmd))#cmd.encode('UTF-8'))
        pass

    def read(self, until=UART_DELIMITER_RX):
        ret = self.ser.read_until(until)
        #print(ret)
        return self._result_of(ret), self._data_of(ret)

    def _read_data(self, until=UART_DELIMITER_RX):
        #while True:
        #    print(self.ser.read())
        res, data = self.read(until)
        if res != self.COMMAND_HANDLED:
            raise CommandError(data)
        return data

    def command_sync(self, cmd, param=None):
        if param is not None:
            if type(param) is int:
                cmd += d2d.int_to_hex(param)#format(param, '02X')
            else:
                cmd += param
            pass
        self.write(cmd)
        return self._read_data()

    class Param:
        def __init__(self, p100, p1000, p2000, p3000, p4000) -> None:
            self.mV100 = 100 + p100-128
            self.mV1000 = 1000 + p1000-128
            self.mV2000 = 2000 + p2000-128
            self.mV3000 = 3000 + p3000-128
            self.mV4000 = 4000 + p4000-128
            self.a0, self.b0 = self._gen_ab(100, 1000, self.mV100, self.mV1000)
            self.a1, self.b1 = self._gen_ab(1000, 2000, self.mV1000, self.mV2000)
            self.a2, self.b2 = self._gen_ab(2000, 3000, self.mV2000, self.mV3000)
            self.a3, self.b3 = self._gen_ab(3000, 4000, self.mV3000, self.mV4000)
            pass

        def _gen_ab(self, v1, v2, v1_meas, v2_meas):
            return (v2_meas - v1_meas) / (v2 - v1), (v1_meas*v2 - v2_meas*v1) / (v2 - v1)

    def read_params(self):
        self._params = []
        params = d2d.HexStream(hex_array=self.command_sync(cmd='P'), hex_byte=1)
        for i in range(self.CHANNELS):
            p = params.bytes[i*5:]
            #print(p)
            self._params.append(
                self.Param(
                    p[0],
                    p[1],
                    p[2],
                    p[3],
                    p[4],
                    #int(p[:2], 16),
                    #int(p[2:4], 16),
                    #int(p[4:6], 16),
                    #int(p[6:8], 16),
                    #int(p[8:10], 16),
                    )
                    )
        pass

    def _correctedmvolt(self, ch, mvolt):
        param = self._params[ch]
        a = 1
        b = 0
        if mvolt < param.mV1000:
            a = param.a0
            b = param.b0
        elif mvolt < param.mV2000:
            a = param.a1
            b = param.b1
        elif mvolt < param.mV3000:
            a = param.a2
            b = param.b2
        else:
            a = param.a3
            b = param.b3
            pass
        #print(a, b)
        return (mvolt - b) / a

    def _mvolt2code(self, mvolt):
        return d2d.clamp(int(mvolt/self.UNIT_MV), low=self.DAC_MIN, high=self.DAC_MAX)

    def gen_constant(self, ch, mvolt):
        return self.gen_constant_wo_calibration(self._correctedmvolt(ch, mvolt))

    def gen_constant_wo_calibration(self, mvolt):
        wave = []
        fb1=0
        fb2=0
        for i in range(3200):
            fb1 = mvolt - fb2 + fb1
            fb2 = self._mvolt2code(fb1) * self.UNIT_MV
            if fb2 < 0:
                fb2 = 0
            wave.append(self._mvolt2code(fb2))
        return d2d.HexStream(byte_array=wave).gen_hexs()#self._encode(wave)

    pass
