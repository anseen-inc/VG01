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
            print(vg01.command_sync('H'))

            targets = [100, 1000, 2000, 3000, 4000]
            for ch in range(VG01.CHANNELS):
                print('CH' + str(ch))
                vg01.command_sync('I', ch)
                for j in range(len(targets)):
                    t = targets[j]
                    vg01.command_sync(VG01.CH_CODES[ch], vg01.gen_constant(ch=ch, mvolt=t))
                    input('outputting ' + str(t) + ' mV from ch' + str(ch))
                    pass
                pass

        except CommandError as e:
            print(e)

        pass

if __name__ == '__main__':
    main()