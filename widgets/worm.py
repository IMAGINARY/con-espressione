from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Rectangle
from scipy.interpolate import interp1d
from kivy.metrics import dp


class WormWidget(Widget):

    def __init__(self, th, controller, pos_offset=100, **kwargs):
        super(WormWidget, self).__init__(**kwargs)

        self.controller = controller

        # history of positions
        self.positions = [(0.5, 0.5), ]  # initial position
        self.max_len_pos = 40
        self.smoothing_factor = 0.3

        # configure tempo factor and velocity factor range
        self.tempo_fnc = interp1d([0, 0.5, 1], [2, 1, 0.5])
        self.vel_fnc = interp1d([0, 0.5, 1], [0.5, 1, 2])

        self.th = th
        self.size = Window.size
        self.pos_offset = pos_offset
        self.positions_hist = []

    def update(self, *args):
        # limit list of positions to max_len_pos
        self.positions = self.positions[:self.max_len_pos]

        # get postion and smooth
        pos = self.controller.get_pos(smoothing_factor=self.smoothing_factor)

        if pos is None:
            pos = self.positions[0]

        # map position to tempo-factor and velocity-factor
        cur_tempo_factor = self.tempo_fnc(pos[0])
        cur_velocity_factor = self.vel_fnc(pos[1])

        # set the MIDI playback accordingly
        self.th.set_tempo(cur_tempo_factor)
        self.th.set_velocity(cur_velocity_factor)

        # store current position at the beginning of the list
        self.positions.insert(0, pos)
        self.positions_hist.append(pos)

        # draw worm as red trajectory
        self.draw_worm((1, 0, 0))

    def draw_worm(self, color):
        """Draw worm trajectory."""

        self.canvas.clear()

        with self.canvas:
            # debug green
            # Color(0, 1, 0)
            # print(self.pos, self.size)
            # Rectangle(pos=self.pos, size=self.size)

            for cur_t, cur_pos in enumerate(self.positions):
                # color with adjusted alpha channel
                # the older, make more transparent
                Color(*color, mode='rgb',
                      a=1 - cur_t * (1.0 / self.max_len_pos))

                # circle size depends on position in list
                # the older, the smaller
                d = 30.0
                cur_size = d - (d / self.max_len_pos) * cur_t

                # draw circle
                Ellipse(pos=(cur_pos[0] * self.size[0], cur_pos[1] * self.size[1]+self.pos_offset),
                        size=(dp(cur_size), dp(cur_size)))
