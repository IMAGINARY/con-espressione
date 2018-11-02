from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse


class CircleWidget(Widget):
    def __init__(self, **kwargs):
        super(CircleWidget, self).__init__(**kwargs)

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
            self.ellipse = Ellipse(pos=self.pos, size=self.size)

    def update_ell(self, *args):
        self.ellipse.pos = self.pos
        self.ellipse.size = self.size