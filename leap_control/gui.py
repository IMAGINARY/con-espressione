import os
from os import listdir
from os.path import isfile, join

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse
from kivy.clock import Clock
from kivy.uix.dropdown import DropDown

import Leap
import numpy as np
import mido

from midi_thread import MidiThread


def select_port():
    midi_ports = mido.get_output_names()

    for cur_idx, cur_port in enumerate(midi_ports):
        print('{} \t {}'.format(cur_idx, cur_port))

    port_nr = int(input('Select Port: '))
    print('\n')

    return port_nr, midi_ports[port_nr]


def select_midi(midi_path='./midi/'):
    # get available MIDIs
    midi_files = [f for f in listdir(midi_path) if isfile(join(midi_path, f))]

    files = []

    print('Nr \t File')
    for i, file in enumerate(midi_files):
        files.append(join(midi_path, file))
        print('{} \t {}'.format(i, file))

    file_nr = int(input('Select Midi: '))

    return files[file_nr]


class MyPaintWidget(Widget):

    def __init__(self, th):
        super(MyPaintWidget, self).__init__()

        self.controller = Leap.Controller()
        # controller's coordinate system
        self.x_lim = [-200, 200]
        self.y_lim = [100, 400]

        # history of positions
        self.positions = [(0.5, 0.5), ]
        self.max_len_pos = 40
        self.smoothing_factor = 0.3

        # configure tempo factor and velocity range
        self.tf_min = 0.5
        self.tf_max = 2.0
        self.vel_min = 0
        self.vel_max = 128

        self.th = th
        self.size = Window.size

    def update(self, *args):
        # get current frame
        frame = self.controller.frame()

        # only access hand if one is available
        if len(frame.hands) > 0:
            # limit list of positions to max_len_pos
            self.positions = self.positions[:self.max_len_pos]

            # get the first hand
            hand = frame.hands[0]

            # get postion and smooth
            pos = self.get_pos(hand)
            pos = self.smooth(pos)

            # map position to tempo-factor and velocity
            cur_tempo_factor = -(self.tf_max - self.tf_min) * pos[0] + 2.0
            cur_velocity = (self.vel_max - self.vel_min) * pos[1] + self.vel_min

            # set the MIDI playback accordingly
            self.th.set_tempo(cur_tempo_factor)
            self.th.set_velocity(int(cur_velocity))

            # store current position at the beginning of the list
            self.positions.insert(0, pos)

            # draw worm as red trajectory
            self.draw_worm((1, 0, 0))

    def draw_worm(self, color):
        """Draw worm trajectory."""

        self.canvas.clear()

        with self.canvas:
            for i, p in enumerate(self.positions):
                # color with adjusted alpha channel
                # the older, make more transparent
                Color(*color, mode='rgb', a=1 - i * (1.0 / self.max_len_pos))

                # circle size depends on position in list
                # the older, the smaller
                d = 30.0
                size = d - (d / self.max_len_pos) * i

                # draw circle
                Ellipse(pos=(p[0] * self.size[0], p[1] * self.size[1]), size=(size, size))

    def get_pos(self, hand):
        """Get hand position from LeapMotion"""

        # extract palm position (0 ... x-axis, 1 ... y-axis, 2 ... z-axis)
        pos = [hand.palm_position[0], hand.palm_position[1]]

        # set position limits
        pos[0] = max(pos[0], self.x_lim[0])
        pos[0] = min(pos[0], self.x_lim[1])

        pos[1] = max(pos[1], self.y_lim[0])
        pos[1] = min(pos[1], self.y_lim[1])

        # project sensor data to [0, 1]
        pos[0] = pos[0] / 400.0 + 0.5  # x
        pos[1] = pos[1] / 300.0 - 1./3  # y

        return pos

    def smooth(self, pos):
        """Smooth hand trajectory with exponential moving average filter."""

        pos[0] = self.smoothing_factor * pos[0] + (1 - self.smoothing_factor) * self.positions[0][0]
        pos[1] = self.smoothing_factor * pos[1] + (1 - self.smoothing_factor) * self.positions[0][1]

        return pos


class MyPaintApp(App):

    def build(self):
        parent = Widget()

        # dropdown = DropDown()
        # midi_files = select_midi()
        # # for index in range(len(MIDIFILES)):
        # for index in midi_files.keys():
        #
        #     btn = Button(text='{}'.format(midi_files[index]), size_hint_y=None, height=44)
        #     btn.bind(on_release=lambda btn: dropdown.select(midi_files[btn.text]))
        #
        #     dropdown.add_widget(btn)
        #
        # mainbutton = Button(text='Hello', size_hint=(None, None))
        # mainbutton.bind(on_release=dropdown.open)
        #
        # dropdown.bind(on_select=lambda instance, x: setattr(mainbutton, 'text', x))
        #
        #
        # parent.add_widget(mainbutton)
        selected_port, selected_port_name = select_port()
        midi_file = select_midi()

        th = MidiThread(midi_file, selected_port_name)

        self.painter = MyPaintWidget(th)
        parent.add_widget(self.painter)

        Clock.schedule_interval(self.painter.update, 0.05)
        th.start()

        return parent

    def clear_canvas(self, obj):
        self.painter.canvas.clear()


if __name__ == '__main__':
    # Window.fullscreen = True
    MyPaintApp().run()
