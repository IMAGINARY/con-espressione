from kivy.uix.widget import Widget
from kivy.uix.progressbar import ProgressBar
from kivy.graphics.context_instructions import PushMatrix, Rotate, PopMatrix


class VerticalProgressBar(Widget):
    def __init__(self, **kwargs):
        super(VerticalProgressBar, self).__init__(**kwargs)

        with self.canvas:
            # add your instruction for main canvas here
            # self.progress_bar = ProgressBar(max=10, value=0, size=(200, 200))
            self.progress_bar = ProgressBar(max=10, value=0)

        with self.canvas.before:
            # you can use this to add instructions rendered before
            PushMatrix()
            self.rotation = Rotate(angle=90, origin=self.center)

        with self.canvas.after:
            # you can use this to add instructions rendered after
            PopMatrix()