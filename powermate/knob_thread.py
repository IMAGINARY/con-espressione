from threading import Thread
import hid
import mido
import time


class KnobThread(Thread):
    def __init__(self, knob):
        Thread.__init__(self)

        self.knob_pos = 0
        self.knob = knob

        self.VendorID = 0x077d  # 1917
        self.ProductID = 0x0410  # 1040

        self.read = True

        self.device = hid.device()

        try:
            self.device.open(self.VendorID, self.ProductID)

        except IOError:
            self.device = None
            print('knob_thead.py: Could not open knob device!')

    def run(self):

        while self.read and self.device is not None:

            rot = self.device.read(64)[1]
            # other direction is encoded as 255
            if rot >= 127:
                rot = -1  # for opposite direction

            self.knob_pos = max(0, min(self.knob_pos + rot, 100))
            self.knob.value = self.knob_pos

        if self.device is not None:
            self.device.close()
        return 0

    def stop_reading(self):
        self.read = False


class MidiKnobThread(Thread):
    def __init__(self, knob, midi_port='nanoKONTROL2 SLIDER/KNOB'):
        Thread.__init__(self)

        self.knob_pos = 0
        self.knob = knob

        self.midi_port = midi_port

        self.read = True

        try:
            self.inport = mido.open_input(self.midi_port)
        except:
            self.inport = None
            print('Invalid MIDI port')

    def run(self):

        while self.read and self.inport is not None:

            for msg in self.inport:

                if msg.type == 'control_change':
                    self.knob_pos = 100 * msg.value / 127.
                    self.knob.value = self.knob_pos
                    time.sleep(1e-3)

        if self.inport is not None:
            self.inport.close()
        return 0

    def stop_reading(self):
        self.read = False
