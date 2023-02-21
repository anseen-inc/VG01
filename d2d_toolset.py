
class ASCII:
    CR = b'\x0D'
    LF = b'\x0A'

def int_to_hex(i):
    h = hex(i)[2:] # remove prefix '0x'
    if len(h) % 2  == 1:
        h = '0' + h
    return h

def hex_to_int(h):
    return int(h, 16)

def str_to_bytes(s):
    return s.encode('UTF-8')

def bytes_to_str(b):
    return b.decode()

def clamp(x, low=0, high=255):
    return min(high, max(x, low))

class HexStream:
    def __init__(self, byte_array=None, hex_array=None, hex_byte=1) -> None:
        if byte_array is not None:
            self._bytes = byte_array
        elif hex_array is not None:
            self._bytes = []
            n = hex_byte * 2
            for i in range(int(len(hex_array)/n)):
                i *= n
                self._bytes.append(hex_to_int(hex_array[i:i+n]))
        pass
    
    @property
    def bytes(self):
        return self._bytes

    def gen_hexs(self):
        hexs = []
        for b in self.bytes:
            hexs.append(int_to_hex(b))
        return ''.join(hexs)
