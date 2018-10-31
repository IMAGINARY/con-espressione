from threading import Thread
import hid


class KnobThread(Thread):
    def __init__(self, progress_bar):
        Thread.__init__(self)

        self.knob_pos = 0
        self.progress_bar = progress_bar

        self.VendorID = 0x077d  # 1917
        self.ProductID = 0x0410  # 1040

        self.read = True

        self.device = hid.device()

        try:
            self.device.open(self.VendorID, self.ProductID)

        except IOError:
            self.device = None
            print('Invalid device')

    def run(self):

        while self.read and self.device is not None:

            rot = self.device.read(64)[1]
            # other direction is encoded as 255
            if rot >= 127:
                rot = -1  # for opposite direction

            self.knob_pos = max(0, min(self.knob_pos + rot, 100))
            self.progress_bar.set_value(self.knob_pos)

        if self.device is not None:
            self.device.close()
        return 0

    def stop_reading(self):
        self.read = False
