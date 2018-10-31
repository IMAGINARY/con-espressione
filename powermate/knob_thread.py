import glob
from powermate.powermate import PowerMateBase
from threading import Thread


class ExamplePowerMate(PowerMateBase):
    def __init__(self, path, progress_bar):
        super(ExamplePowerMate, self).__init__(path)
        self.pos = 0
        self.progress_bar = progress_bar

    def rotate(self, rotation):
        # one rotation is around 90 rotation ticks, the following lines scale the position to range [0,10]
        self.pos = max(0, min(self.pos+rotation, 90))
        # self.progress_bar.set_value(int(self.pos/9))
        self.progress_bar.set_value(self.pos)



class KnobThread(Thread):
    def __init__(self, progress_bar):
        Thread.__init__(self)
        self.pm = ExamplePowerMate(glob.glob('/dev/input/by-id/*PowerMate*')[0], progress_bar)

    def run(self):
        self.pm.run()
