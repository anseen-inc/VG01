import serial
import serial.tools.list_ports

from vg01 import *
from matplotlib import pyplot as plt
plt.switch_backend('TkAgg')

def main():
    comports = serial.tools.list_ports.comports()
    i = 0
    for i, port in enumerate(comports):
        print("%d: %s" % (i, port))
        pass

    i = input("enter port index: ")
    port = None
    try:
        port = comports[int(i)]
        pass
    except ValueError:
        print("invalid input")
        exit()

    with serial.Serial(port.device, 115200) as ser:
        try:
            vg01 = VG01(ser, echo=False)
            print(vg01.read_all())
            vg01.command_sync('H')

            targets = [100, 1000, 2000, 3000, 4000]
            for i in range(VG01.CHANNELS):
                print('CH' + str(i))
                vg01.command_sync('I', i)
                for j in range(len(targets)):
                    t = targets[j]
                    vg01.command_sync(VG01.CH_CODES[i], vg01.gen_constant_wo_calibration(t))
                    mv = input('enter output voltage [mV]: ')
                    value = (int(mv)-t+128) & 0xFF
                    addr = (VG01.ADDR_PARAMS_START + i*len(targets) + j) << 8
                    vg01.command_sync('Z', addr + value)
                    pass
                pass

        except CommandError as e:
            print(e)

        pass

if __name__ == '__main__':
    main()