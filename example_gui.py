import tkinter as tk
import tkinter.messagebox

import serial
import serial.tools.list_ports
import threading
import queue
import re
from vg01 import *


class Application(tk.Frame):
    def __init__(self, root, vg01):
        super().__init__(root)
        self._root = root
        self._vg01 = vg01
        self.reconnect_is_requested = False

        self._root.title('VG01: ' + self._vg01.ser.name)
        self.pack()
  
        self.create_widgets()
        self.start_up()

    def cleanup(self):
        self.queue_tx.put(None)
        self._root.after_cancel(self._update_jobid)

    class AWG_Frame(tk.Frame):
        def __init__(self, parent, ch, app) -> None:
            super().__init__(parent)
            self._ch = str(ch)
            self._app = app
            
            self._ch_label = tk.Label(self, text='CH' + self._ch)
            self._ch_label.pack(pady=10)

            size = 20
            self._canvas = tk.Canvas(self, width=size, height=size)
            self._canvas.create_oval(2, 2, size, size, fill='gray', tag='led')
            self._canvas.bind('<Button-1>', self._on_click)
            self._canvas.pack(pady=10)
            
            self._mvolt_frame = tk.Frame(self)
            self._mvolt_re = re.compile('[0-9]+')
            self._mvolt_valcmd = self.register(self._on_validate)
            self._mvolt = tk.StringVar()
            self._mvolt_entry = tk.Entry(self._mvolt_frame, textvariable=self._mvolt, validate='key', validatecommand=(self._on_validate, '%S'), width=5, justify='right')
            self._mvolt_entry.pack(side=tk.LEFT, padx=0)
            self._mvolt_label = tk.Label(self._mvolt_frame, text='mV')
            self._mvolt_label.pack(side=tk.LEFT, padx=0)
            self._mvolt_frame.pack(pady=0)

            self._button_frame = tk.Frame(self)
            self._mvolt_set = tk.Button(self, text='Set', command=self._on_set)
            self._mvolt_set.pack(pady=0, fill=tk.X)
            self._button_frame.pack(pady=10)

            pass

        def _on_click(self, event):
            if self._output:
                self._output = False
                self._canvas.itemconfig(tagOrId='led', fill='gray')
                self._app.send_command('O', self._ch)
            else:
                self._output = True
                self._canvas.itemconfig(tagOrId='led', fill='lime')
                self._app.send_command('I', self._ch)

        def _on_validate(self, S):
            if self._mvolt_re.match(S):
                return True
            return False

        def _on_set(self):
            mv = self._mvolt.get()
            if len(mv) == 0:
                self._mvolt.set('0')
            else:
                mv = int(mv)
                if mv < 0:
                    self._mvolt.set('0')
                elif mv > 4000:
                    self._mvolt.set('4000')
                else:
                    self._app.set_wave_constant(ch=int(self._ch), mvolt=mv)
            pass

        def update(self):
            # initialize
            self._mvolt.set('0')
            self._output = True
            self._on_click(None)

        pass

    def _on_recconect(self):
        self.reconnect_is_requested = True
        self.cleanup()
        self._root.destroy()

    def create_widgets(self):
        self._reconnect = tk.Button(self._root, text='Reconnect', command=self._on_recconect)
        self._reconnect.pack(anchor=tk.E, padx=10)
        self._ch_container = tk.Frame(self._root)
        self._awgs = [self.AWG_Frame(parent=self._ch_container, ch=i, app=self) for i in range(VG01.CHANNELS)]
        for awg in self._awgs:
            awg.pack(side=tk.LEFT, padx=10)
        self._output_label = tk.Label(self._ch_container, text='Click on each circle\n to toggle each output on/off.', justify='left')
        self._output_label.pack(side=tk.LEFT, padx=10)
        self._ch_container.pack()

        self.terminal_container = tk.Frame(self._root)
        self.terminal_container.pack(padx=10, pady=10)
        self.log_frame = tk.Frame(self.terminal_container)
        self.log_frame.pack(padx=10, pady=10)
        self.command_frame = tk.Frame(self.terminal_container)
        self.command_frame.pack(padx=10, pady=10)

        # for terminal
        h = 6
        self.log = tk.Text(self.log_frame, height=h)
        self.log.pack(side=tk.LEFT)
        self.log_scrollbar = tk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log.yview)
        self.log.yscrollcommand = self.log_scrollbar.set
        self.log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.command_var = tk.StringVar()
        self.command = tk.Entry(self.command_frame, textvariable=self.command_var)
        self.command.bind('<Return>', self._on_command_enter)
        self.command.pack()
        self.command.focus()

        self.log.bind('<Configure>', lambda e: self.command.configure(width=int(self.log_frame.winfo_width()/h)))

    def start_up(self):
        self.queue_rx = queue.Queue()
        self.queue_tx = queue.Queue()

        self.thread_rx = threading.Thread(target=receiver, args=(self._vg01, self.queue_rx,))
        self.thread_tx = threading.Thread(target=transfer, args=(self._vg01, self.queue_tx,))
        self.thread_rx.daemon = True
        self.thread_tx.daemon = True
        self.thread_rx.start()
        self.thread_tx.start()

        for awg in self._awgs:
            awg.update()
        self.update()
        self.send_command('H')

    def update(self):
        while not self.queue_rx.empty():
            event = self.queue_rx.get()
            t = type(event)
            if t == EventResponse:
                self._add_log(event.response)
            elif t == EventError:
                self._add_log(event.response)
            self.queue_rx.task_done()
        self._update_jobid = self._root.after(10, self.update)

    def _on_command_enter(self, key):
        cmd = self.command_var.get()
        self.send_command(cmd)
        self.command.delete(0, tk.END)

    def send_command(self, cmd, param=None):
        if param is not None:
            cmd += param
        self.queue_tx.put(cmd)
        self._add_log(cmd)

    def _add_log(self, log):
        self.log.insert(tk.END, log + '\n')
        self.log.see(tk.END)

    def set_wave_constant(self, ch, mvolt):
        self.send_command(VG01.CH_CODES[ch], self._vg01.gen_constant(ch, mvolt))

class EventResponse():
    def __init__(self, response):
        self.response = response.decode('UTF-8', errors='ignore').replace('\r', '\n')

class EventError():
    def __init__(self, response):
        self.response = response.decode('UTF-8', errors='ignore').replace('\r', '\n')

def receiver(mca, queue):
    try:
        while True:
            res, data = mca.read()
            if res != mca.COMMAND_HANDLED:
                # error
                queue.put(EventError(data+res))
            else:
                queue.put(EventResponse(data+res))
    except Exception as e:
        # force stop by an exception
        #print(e)
        pass

def transfer(vg, queue):
    while True:
        command = queue.get()
        if command is None:
            break
        n = int(len(command)/VG01.USB_BUFFER_SIZE)
        if n == 0:
            vg.write(command)
        else:
            for i in range(n):
                if i+1 == n:
                    cmd = command[i*VG01.USB_BUFFER_SIZE:]
                else:
                    cmd = command[i*VG01.USB_BUFFER_SIZE:(i+1)*VG01.USB_BUFFER_SIZE]
                vg.write_raw(cmd)
            vg.write('') # send delimitor
        queue.task_done()

class ComportDialog(tk.Frame):
    def __init__(self, root, result_list):
        super().__init__(root)
        self._root = root
        self.result_list = result_list

        self._root.title('Select COM port')
        #self._root.geometry('480x320')
        self.pack(padx=10, pady=10)

        self.create_widgets()

    def create_widgets(self):
        self.comports = serial.tools.list_ports.comports()

        self.ports_frame = tk.Frame(self._root)
        self.ports_frame.pack(padx=10, pady=10)
        self.buttons_frame = tk.Frame(self._root)
        self.buttons_frame.pack(padx=10, pady=10)

        # for comport list
        self.listbox = tk.Listbox(self.ports_frame, width=100, height=10)
        for port in self.comports:
            self.listbox.insert(tk.END, port)
        self.scrollbar_y = tk.Scrollbar(self.ports_frame, command=self.listbox.yview, orient=tk.VERTICAL)
        self.listbox.yscrollcommand = self.scrollbar_y.set
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT)

        # for buttons
        self.connect_button = tk.Button(self.buttons_frame, text='Connect', command=self.onConnectClicked)
        self.connect_button.pack()

    def onConnectClicked(self):
        itemlist = self.listbox.curselection()
        if len(itemlist) == 1:
            self.result_list.append(self.comports[itemlist[0]])
            self._root.destroy()
        else:
            tk.messagebox.showerror("COM port error", "Select a COM port from list")

def connect(root):
    comport = []
    dialog = ComportDialog(root=root, result_list=comport)
    dialog.mainloop()
    return comport

def main():
    while True:
        root = tk.Tk()
        comport = []
        dialog = ComportDialog(root=root, result_list=comport)
        dialog.mainloop()
        if len(comport) != 1:
            break
        else:
            with serial.Serial(comport[0].device, 115200) as ser:
                vg01 = VG01(ser, echo=False)
                root = tk.Tk()
                app = Application(root=root, vg01=vg01)
                app.mainloop()
                app.cleanup()
                if not app.reconnect_is_requested:
                    break

if __name__ == "__main__":
    main()
