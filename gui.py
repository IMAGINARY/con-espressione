"""
Run the GUI demo

TODO
----

* Add external controller (PowerMate)
* Add config file for pre-processing BM performance?
* Improve user interface for setting up the demo 
  (add a proper before the worm visualization?)
"""
import os

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse
from kivy.clock import Clock
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button

import mido

from midi_thread import MidiThread, BasisMixerMidiThread
import controller


def select_port():
    midi_ports = mido.get_output_names()

    for cur_idx, cur_port in enumerate(midi_ports):
        print('{} \t {}'.format(cur_idx, cur_port))

    port_nr = int(input('Select Port: '))
    print('\n')

    return port_nr, midi_ports[port_nr]


def select_file(file_path='./midi/', file_type='Midi'):
    # get available MIDIs
    midi_files = [f for f in os.listdir(
        file_path) if os.path.isfile(os.path.join(file_path, f))]

    files = []

    print('Nr \t File')
    for i, file in enumerate(midi_files):
        files.append(os.path.join(file_path, file))
        print('{} \t {}'.format(i, file))

    file_nr = int(input('Select {0}: '.format(file_type)))

    return files[file_nr]


class MyPaintWidget(Widget):

    def __init__(self, th, controller):
        super(MyPaintWidget, self).__init__()

        self.controller = controller

        # history of positions
        self.positions = [(0.5, 0.5), ]  # initial position
        self.max_len_pos = 40
        self.smoothing_factor = 0.3

        # configure tempo factor and velocity range
        self.tf_min = 0.5
        self.tf_max = 2.0
        self.vel_min = 10
        self.vel_max = 128

        self.th = th
        self.size = Window.size

        self.positions_hist = []

    def update(self, *args):
        # limit list of positions to max_len_pos
        self.positions = self.positions[:self.max_len_pos]

        # get postion and smooth
        pos = self.controller.get_pos(smoothing_factor=self.smoothing_factor)

        if pos is None:
            pos = self.positions[0]

        # map position to tempo-factor and velocity
        cur_tempo_factor = -(self.tf_max - self.tf_min) * pos[0] + 2.0
        cur_velocity = (self.vel_max - self.vel_min) * pos[1] + self.vel_min

        # set the MIDI playback accordingly
        self.th.set_tempo(cur_tempo_factor)
        self.th.set_velocity(int(cur_velocity))

        # store current position at the beginning of the list
        self.positions.insert(0, pos)
        self.positions_hist.append(pos)

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
                Ellipse(pos=(p[0] * self.size[0], p[1] *
                             self.size[1]), size=(size, size))


class MyPaintApp(App):

    def __init__(self, my_controller):
        App.__init__(self)

        self.my_controller = my_controller

    def build(self):
        parent = Widget()

        # dropdown = DropDown()
        # midi_files = select_file()
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

        self.painter = MyPaintWidget(th, self.my_controller)
        parent.add_widget(self.painter)

        Clock.schedule_interval(self.painter.update, 0.05)
        th.start()

        return parent

    def clear_canvas(self, obj):
        self.painter.canvas.clear()


if __name__ == '__main__':
    selected_port, selected_port_name = select_port()

    demo_type = int(input('Use MIDI (type 0) or BM (type 1) file as input?: '))

    if demo_type == 0:
        print('Using MIDI file as input')
        midi_file = select_file()
        th = MidiThread(midi_file, selected_port_name)

    elif demo_type == 1:
        print('Using BM file as input')
        deadpan = int(input('Deadpan performance (type 1)?: '))

        if deadpan == 1:
            deadpan = True
        else:
            deadpan = False
        bm_file = select_file(file_path='./bm_files', file_type='BM file')
        th = BasisMixerMidiThread(bm_file, selected_port_name,
                                  deadpan=deadpan)

    use_lm = int(input('Use LeapMotion? (type 1): '))

    if use_lm == 1:
        # check if leap motion tracker is available
        my_controller = controller.LeapMotion()
    else:
        # use mouse fallback
        my_controller = controller.Mouse()

    MyPaintApp(my_controller).run()
