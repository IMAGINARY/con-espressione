"""
Run the Demo

TODO
----

* Add external controller (PowerMate)
* Add config file for pre-processing BM performance?
* Improve user interface for setting up the demo
  (before the worm visualization?)
"""
import os
import json


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
import threading
import queue

from basismixer.midi_controller import (MIDIController,
                                        DummyMIDIController)
# import multiprocessing as mp


def select_port():
    midi_ports = mido.get_output_names()

    for cur_idx, cur_port in enumerate(midi_ports):
        print('{} \t {}'.format(cur_idx, cur_port))

    try:
        port_nr = int(input('Select Port (default is 0): '))
    except ValueError:
        port_nr = 0
    # port_nr = int(input('Select Port: '))
    print('\n')

    return port_nr, midi_ports[port_nr]


def select_file(file_path='./midi/', file_type='Midi'):
    # get available MIDIs
    all_files = [f for f in os.listdir(
        file_path) if os.path.isfile(os.path.join(file_path, f))]

    files = []

    print('Nr \t File')
    for i, file in enumerate(all_files):
        if file_type == 'Midi' and '.mid' in file:
            files.append(os.path.join(file_path, file))

        elif file_type == 'BM file' and '.txt' in file:
            files.append(os.path.join(file_path, file))

        elif file_type == 'JSON file' and '.json' in file:
            files.append(os.path.join(file_path, file))

    for i, file in enumerate(files):
        print('{} \t {}'.format(i, file))

    try:
        file_nr = int(input('Select {0}: '.format(file_type)))
    except ValueError:
        file_nr = 0
    # file_nr = int(input('Select {0}: '.format(file_type)))

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
        bm_controller.start()

        return parent

    def clear_canvas(self, obj):
        self.painter.canvas.clear()


if __name__ == '__main__':
    selected_port, selected_port_name = select_port()

    try:
        demo_type = int(
            input('Use MIDI (type 0) or BM (type 1) file as input? (Default BM): '))
    except ValueError:
        demo_type = 1

    if demo_type == 0:
        print('Using MIDI file as input')
        midi_file = select_file()
        th = MidiThread(midi_file, selected_port_name)

    elif demo_type == 1:
        print('Using BM file as input')
        try:
            deadpan = int(input('Deadpan performance (type 1)?: '))
        except ValueError:
            deadpan = 0

        if deadpan == 1:
            deadpan = True
        else:
            deadpan = False
        bm_file = select_file(file_path='./bm_files', file_type='BM file')
        # Load config file
        config_file = select_file(file_path='./config_files',
                                  file_type='JSON file')

        config = json.load(open(config_file))

        if 'vel_min' in config:
            vel_min = config.pop('vel_min')
        else:
            vel_min = 30

        if 'vel_max' in config:
            vel_max = config.pop('vel_max')
        else:
            vel_max = 110

        if 'tempo_ave' in config:
            tempo_ave = config.pop('tempo_ave')
        else:
            # This tempo is for the Etude Op 10 No 3
            tempo_ave = 55

        if 'velocity_ave' in config:
            velocity_ave = config.pop('velocity_ave')
        else:
            velocity_ave = 50

        try:
            use_bm_controller = int(
                input('Use controller for the BM (type 1, default is 0)? '))
        except ValueError:
            use_bm_controller = 0

        if use_bm_controller:
            # import powermate
            q_dial = queue.Queue()
            input_midi_ports = mido.get_input_names()

            for cur_idx, cur_port in enumerate(input_midi_ports):
                print('{} \t {}'.format(cur_idx, cur_port))

            try:
                port_nr = int(input('Select Port (default is 0): '))
            except ValueError:
                port_nr = 0
            # port_nr = int(input('Select Port: '))
            print('\n')

            bm_controller = MIDIController(input_midi_ports[port_nr],
                                           q_dial)
            # bm_controller = threading.Thread(
            #     target=powermate.run_device, args=(q_dial,))
            # bm_controller.start()
            
        else:
            bm_controller = DummyMIDIController()
            q_dial = None

        th = BasisMixerMidiThread(bm_file,
                                  midi_port=selected_port_name,
                                  vel_min=vel_min,
                                  vel_max=vel_max,
                                  tempo_ave=tempo_ave,
                                  velocity_ave=velocity_ave,
                                  deadpan=deadpan,
                                  post_process_config=config,
                                  bm_queue=q_dial,
                                  # bm_controller=bm_controller
                                  )

    # use_lm = int(input('Use LeapMotion? (type 1): '))
    try:
        use_lm = int(
            input('Use LeapMotion? (type 1, otherwise use Mouse): '))
    except ValueError:
        use_lm = 0

    if use_lm == 1:
        # check if leap motion tracker is available
        my_controller = controller.LeapMotion()
    else:
        # use mouse fallback
        my_controller = controller.Mouse()

    MyPaintApp(my_controller).run()
