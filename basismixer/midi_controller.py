import hid
import threading
import mido
import time
import numpy as np


class MIDIController(threading.Thread):

    def __init__(self, midi_port, out_q):

        threading.Thread.__init__(self)
        self.midi_port = midi_port
        self.out_q = out_q

    def run(self):

        with mido.open_input(self.midi_port) as inport:

            for msg in inport:

                if msg.type == 'control_change':
                    value = float(msg.value) / 127.
                    self.out_q.put(value)
                time.sleep(1e-3)


class PowerMate(threading.Thread):
    def __init__(self, out_q,
                 VendorID=0x077d, ProductID=0x0410,
                 init_value=0.5):
        # Initialize device
        self.device = hid.device()
        try:
            self.device.open(VendorID, ProductID)

        except IOError:
            raise IOError('Invalid device')
        self.out_q = out_q
        self.init_value = init_value

    def run(self):
        value = self.init_value
        mult = 0.01
        try:
            while True:
                d = self.device.read(64)
                if d:
                    left = float(d[1] > 250)
                    right = float(d[1] >= 1 and d[1] <= 10)
                    button = d[0]
                    value += mult * (right - left)

                    if button:
                        value = self.init_value

                    value = np.clip(value,
                                    a_min=0.0,
                                    a_max=1.0)
                    self.out_q.put(value)
        except KeyboardInterrupt:
            return 0


class DummyMIDIController(object):
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass
