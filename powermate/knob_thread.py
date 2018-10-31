from threading import Thread
import usb


class KnobThread(Thread):
    def __init__(self, progress_bar):
        Thread.__init__(self)

        self.pos = 0
        self.progress_bar = progress_bar

        VENDOR = 0x077d  # 1917
        PRODUCT = 0x0410  # 1040

        self.dev = usb.core.find(idVendor=VENDOR, idProduct=PRODUCT)

        if self.dev is None:
            raise Exception("Could not find Griffin PowerMate.")

        # otherwise the kernel is busy
        if self.dev.is_kernel_driver_active(0):
            self.dev.detach_kernel_driver(0)

        self.dev.set_configuration()

    def run(self):
        # self.pm.run()
        while self.dev.read(129, 6, timeout=99999999999)[0] == 0:

            rot = self.dev.read(129, 6, timeout=99999999999)[1]

            # other direction is encoded as 255
            if rot >= 127:
                rot = -1  # for opposite direction

            self.pos = max(0, min(self.pos + rot, 90))
            self.progress_bar.set_value(self.pos)

