from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse


class CircleWidget(Widget):
    def __init__(self, **kwargs):
        super(CircleWidget, self).__init__(**kwargs)

        self.draw()

    def draw(self):
        with self.canvas:
            # Empty canvas instructions
            self.canvas.clear()

            # Draw no-progress circle
            Color(0.26, 0.26, 0.26)
            Ellipse(pos=self.pos, size=self.size)
