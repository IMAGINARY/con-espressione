from kivy.app import App
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse
from kivy.clock import Clock

import os, sys, inspect
# import leap motion (unfortunately there is no pip package for installing)
src_dir = os.path.dirname(inspect.getfile(inspect.currentframe()))
arch_dir = './lib/x64' if sys.maxsize > 2**32 else './lib/x86'
sys.path.insert(0, os.path.abspath(os.path.join(src_dir, arch_dir)))

import Leap

from midi_thread import MidiThread
# from thread_test import select_port, select_midi
import numpy as np

from kivy.uix.dropdown import DropDown
from subprocess import Popen, PIPE
import re
from os import listdir
from os.path import isfile, join



def select_port():
    p = Popen(['aplaymidi', '-l'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = p.communicate(b"input data that is passed to subprocess' stdin")

    output = output.split('\n')[1:]

    port_dict = {}

    print('Nr \t Port')
    for i, elem in enumerate(output):

        split = re.split(r'\s{2,}', elem)

        if len(split) > 1:
            port_dict[i] = split

            print('{} \t {}'.format(i, split[1]))

    port_nr = input('Select Port: ')
    print('\n')

    return port_dict[port_nr][-1]


def select_midi(midi_path='./midi/'):

    midi_files = [f for f in listdir(midi_path) if isfile(join(midi_path, f))]

    file_dict = {}

    print('Nr \t File')
    for i, file in enumerate(midi_files):
        file_dict[i] = join(midi_path, file)

        print('{} \t {}'.format(i, file))

    file_nr = input('Select Midi: ')
    return file_dict[file_nr]

# def select_midi():
#
#     midi_path = '../midi/'
#     midi_files = [f for f in listdir(midi_path) if isfile(join(midi_path, f))]
#
#     files = {}
#
#     for i, file in enumerate(midi_files):
#         files[i] = join(midi_path, file)
#
#     return files

class MyPaintWidget(Widget):

    def __init__(self, th):
        super(MyPaintWidget, self).__init__()

        self.controller = Leap.Controller()
        self.positions = []
        self.max_len_pos = 20


        self.th = th
        self.size = Window.size



    def update(self, *args):
        color = (1, 0, 0)

        frame = self.controller.frame()

        y_lim = [100, 400]
        x_lim = [-200, 200]

        velocity = np.linspace(100, 400, num=128)
        tempo = np.linspace(0.5, 2, num=400)

        x_loc = np.linspace(-200, 200, num=400)

        # only access hand if one is available
        if len(frame.hands) > 0:

            if len(self.positions) >= self.max_len_pos:
                self.positions = self.positions[0:-1]

            # get the first hand
            hand = frame.hands[0]

            # extract palm position (0 ... x-axis, 1 ... y-axis, 2 ... z-axis)
            pos = [hand.palm_position[0], hand.palm_position[1]]

            # set position limits
            if pos[0] < x_lim[0]:
                pos[0] = x_lim[0]
            elif pos[0] > x_lim[1]:
                pos[0] = x_lim[1]

            if pos[1] < y_lim[0]:
                pos[1] = y_lim[0]
            elif pos[1] > y_lim[1]:
                pos[1] = y_lim[1]


            vel = sum(velocity < pos[1])

            temp = tempo[sum(x_loc > pos[0])]

            self.th.set_velocity(vel)
            self.th.set_tempo(temp)

            pos[1] = pos[1]/300.0 - 1./3
            pos[0] = pos[0]/400.0 + 0.5

            # store position at the beginning of the list
            self.positions.insert(0, pos)

            # print(note, vel)
            # msg = mido.Message('note_on', note=note, velocity=vel)

            print(pos[0], pos[1])

            self.canvas.clear()
            with self.canvas:
                for i, p in enumerate(self.positions):
                    Color(*color, mode='rgb', a=1-i*(1.0/self.max_len_pos))
                    d = 30.
                    size = d-(d/self.max_len_pos)*i
                    Ellipse(pos=(p[0]*self.size[0], p[1]*self.size[1]), size=(size, size))


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
        selected_port = select_port()
        #
        midi_file = select_midi()
        th = MidiThread(midi_file, selected_port)

        self.painter = MyPaintWidget(th)
        parent.add_widget(self.painter)

        Clock.schedule_interval(self.painter.update, 0.05)
        th.start()

        return parent

    def clear_canvas(self, obj):
        self.painter.canvas.clear()


if __name__ == '__main__':
    MyPaintApp().run()