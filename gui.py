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
os.environ['KIVY_VIDEO'] = 'ffpyplayer'
import json

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.videoplayer import VideoPlayer

import mido

from midi_thread import MidiThread, BasisMixerMidiThread
import controller
import queue

# from basismixer.midi_controller import MIDIController, DummyMIDIController
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


class WormWidget(Widget):

    def __init__(self, th, controller):
        super(WormWidget, self).__init__()

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


class LeapControl(App):
    def __init__(self, worm_controller,
                 midi_port, fn_midi):
        App.__init__(self)
        self.worm_controller = worm_controller
        self.playback_thread = None
        self.midi_port = midi_port
        self.fn_midi = fn_midi
        self.fn_video = os.path.join(os.path.dirname(__file__), 'test.mp4')

    def build(self):
        # basic layout blocks
        self.root = BoxLayout(orientation='vertical')
        self.scm = ScreenManager(transition=SlideTransition())
        self.root.add_widget(self.scm)

        # Navigation
        self.root.add_widget(self.navigation())

        # add screens to screen manager
        replay_screen = Screen(name='replay')
        self.scm.add_widget(replay_screen)

        intro_screen = Screen(name='intro')
        path_video = os.path.join(self.fn_video)
        player = VideoPlayer(source=path_video)
        intro_screen.add_widget(player)
        self.scm.add_widget(intro_screen)
        self.scm.current = 'intro'

        return self.root

    def navigation(self):
        navigation = BoxLayout(height=48, size_hint_y=None)
        bt_intro = Button(text='Intro', height=48, size_hint_y=None,
                          on_release=lambda a: self.screen_intro())
        bt_demo = Button(text='Demo', height=48, size_hint_y=None,
                         on_release=lambda a: self.screen_demo())
        bt_replay = Button(text='Replay', height=48, size_hint_y=None,
                           on_release=lambda a: self.set_screen('replay'))
        navigation.add_widget(bt_intro)
        navigation.add_widget(bt_demo)
        navigation.add_widget(bt_replay)

        return navigation

    def screen_intro(self):
        self.scm.current = 'intro'

        if self.playback_thread is not None:
            self.playback_thread.stop_playing()

    def screen_demo(self):
        # This is a hack
        # We rebuild the demo screen when called
        # to reset the playback.
        for cur_screen in self.scm.screens:
            if cur_screen.name == 'demo':
                # delte old demo screen
                self.scm.remove_widget(cur_screen)
                break

        self.playback_thread = MidiThread(self.fn_midi, self.midi_port)
        self.playback_thread.daemon = True

        # create a new one
        demo_screen = Screen(name='demo')
        self.painter = WormWidget(self.playback_thread, self.worm_controller)
        demo_screen.add_widget(self.painter)
        Clock.schedule_interval(self.painter.update, 0.05)
        self.scm.add_widget(demo_screen)

        self.scm.current = 'demo'
        self.playback_thread.start()

    def set_screen(self, screen_name):
        # self.midi_thread.stop()
        self.scm.current = screen_name

        if self.playback_thread is not None:
            self.playback_thread.stop_playing()

    def clear_canvas(self, obj):
        self.painter.canvas.clear()


if __name__ == '__main__':
    _, selected_midi_port = select_port()

    # Get the demo type:
    try:
        demo_type = int(input('Use MIDI (type 0) or BM (type 1) file as input? (Default BM): '))
    except ValueError:
        demo_type = 1

    if demo_type == 0:
        print('Using MIDI file as input')
        fn_midi = select_file()
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

        # Load BM file
        bm_file = select_file(file_path='./bm_files', file_type='BM file')

        # Load config file
        config_file = select_file(file_path='./config_files', file_type='JSON file')
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
            use_bm_controller = int(input('Use controller for the BM (type 1, default is 0)? '))
        except ValueError:
            use_bm_controller = 0

        # Use the USB controller for scaling BM's parameters
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

            # bm_controller = MIDIController(input_midi_ports[port_nr],
            #                                q_dial)
            # bm_controller = threading.Thread(
            #     target=powermate.run_device, args=(q_dial,))
            # bm_controller.start()
        else:
            # bm_controller = DummyMIDIController()
            q_dial = None

        # playback_thread = BasisMixerMidiThread(bm_file,
        #                                        midi_port=selected_port_name,
        #                                        vel_min=vel_min,
        #                                        vel_max=vel_max,
        #                                        tempo_ave=tempo_ave,
        #                                        velocity_ave=velocity_ave,
        #                                        deadpan=deadpan,
        #                                        post_process_config=config,
        #                                        bm_queue=q_dial,
        #                                        # bm_controller=bm_controller
        #                                        )

    # use_lm = int(input('Use LeapMotion? (type 1): '))
    try:
        use_lm = int(input('Use LeapMotion? (type 1, otherwise use Mouse): '))
    except ValueError:
        use_lm = 0

    if use_lm == 1:
        # check if leap motion tracker is available
        worm_controller = controller.LeapMotion()
    else:
        # use mouse fallback
        worm_controller = controller.Mouse()

    # run the app
    LeapControl(worm_controller,
                midi_port=selected_midi_port,
                fn_midi=fn_midi).run()
