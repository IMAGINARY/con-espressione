from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse
import numpy as np


class CircleWidget(Widget):
    def __init__(self, color, **kwargs):
        super(CircleWidget, self).__init__(**kwargs)

        self.color = color
        self.draw()
        self.bind(pos=self.update_ell,
                  size=self.update_ell)



    def draw(self):
        with self.canvas:
            # Empty canvas instructions
            self.canvas.clear()

            # Draw circle
            Color(0.26, 0.26, 0.26)
            # Ellipse(pos=self.pos, size=self.size)
            self.ellipse = Ellipse(pos=self.pos, size=self.size, color=Color(*self.color, 1))

    def update_widget(self, scale):
        print(scale)

        scale = np.min(np.atleast_1d(scale))


        # print(max(self.size[0] * scale, 0.01), max(self.size[1] * scale, 0.01))
        self.ellipse.size = [max(self.size[0] * (scale), 0.01), max(self.size[1] * (scale), 0.01)]

    def update_ell(self, *args):
        self.ellipse.pos = self.pos
        self.ellipse.size = self.size