import glob
from powermate.powermate import PowerMateBase
from threading import Thread


class ExamplePowerMate(PowerMateBase):
    def __init__(self, path, progress_bar, label):
        super(ExamplePowerMate, self).__init__(path)
        self.pos = 0
        self.progress_bar = progress_bar
        self.label = label

    def rotate(self, rotation):
        # one rotation is around 90 rotation ticks, the following lines scale the position to range [0,10]
        self.pos = max(0, min(self.pos+rotation, 90))
        self.progress_bar.value = int(self.pos/9)
        self.label.text = str(self.progress_bar.value)


class KnobThread(Thread):
    def __init__(self, progress_bar, label):
        Thread.__init__(self)
        self.pm = ExamplePowerMate(glob.glob('/dev/input/by-id/*PowerMate*')[0], progress_bar, label)

    def run(self):
        self.pm.run()
