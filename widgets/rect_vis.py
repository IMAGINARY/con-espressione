from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.uix.label import Label
import numpy as np
from kivy.metrics import dp


class RectangleWidget(Widget):
    def __init__(self, name, color, **kwargs):
        super(RectangleWidget, self).__init__(**kwargs)

        self.name = name
        self.color = color
        self.draw()
        self.bind(pos=self.update_rect,
                  size=self.update_rect)

    def draw(self):
        with self.canvas:
            # Empty canvas instructions
            self.canvas.clear()

            # Draw circle
            Color(*self.color, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
            self.label = Label(text=self.name, font_size='15sp', pos=self.pos)


    def update_widget(self, scale):
        scale = np.min(np.atleast_1d(scale))

        self.rect.size = [self.size[0], max(self.size[1] * (scale), 0.01)]

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

        self.label.pos = [self.pos[0]-dp(10), self.pos[1]-dp(60)]
