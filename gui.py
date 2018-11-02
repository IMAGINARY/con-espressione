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
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.videoplayer import VideoPlayer
from kivy.graphics import Color

from kivy.uix.relativelayout import RelativeLayout
from powermate.knob_thread import KnobThread
from widgets.worm import WormWidget
from widgets.circle_vis import CircleWidget
import mido

from midi_thread import MidiThread, BasisMixerMidiThread
import controller
import queue
from kivy.config import Config
from kivy.uix.floatlayout import FloatLayout
from widgets.knob import Knob

Config.set('graphics', 'fullscreen', 0)
Config.write()
# from basismixer.midi_controller import MIDIController, DummyMIDIController
# import multiprocessing as mp


def load_files(file_path='./midi/', file_type='Midi'):
    # get available MIDIs
    all_files = [f for f in os.listdir(
        file_path) if os.path.isfile(os.path.join(file_path, f))]

    files = []

    for i, file in enumerate(all_files):
        if file_type == 'Midi' and '.mid' in file:
            files.append(os.path.join(file_path, file))

    return files


class LeapControl(App):
    def __init__(self):
        App.__init__(self)

        self.worm_controller = None
        self.playback_thread = None
        self.knob_thread = None
        self.midi_port = None
        self.fn_midi = None
        self.fn_video = os.path.join(os.path.dirname(__file__), 'test.mp4')

    def build_config(self, config):

        config.setdefaults('settings', {
            'playmode': 'MIDI',
            'midiport': 'Midi Through:Midi Through Port-0 14:0',
            'control': 'Mouse',
            'song': 'bach.mid'
        })

    def get_worm_controller(self):
        worm_controller = controller.Mouse()
        if self.config.get('settings', 'control') == 'LeapMotion':
            # check if leap motion tracker is available
            worm_controller = controller.LeapMotion()
        return worm_controller

    def get_song_path(self):

        return os.path.join('./midi/', self.config.get('settings', 'song'))

    def get_midi_port(self):
        return self.config.get('settings', 'midiport')

    def build(self):

        self.worm_controller = self.get_worm_controller()
        self.fn_midi = self.get_song_path()
        self.fn_midi = self.get_song_path()

        # basic layout blocks
        self.root = StackLayout()
        self.scm = ScreenManager(transition=SlideTransition(), size_hint=(1.0, 0.9))
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

    def on_config_change(self, config, section, key, value):

        if section == "settings":
            if key == "midiport":
                self.midi_port = value
            if key == 'control':
                self.worm_controller = self.get_worm_controller()
            if key == 'song':
                self.fn_midi = self.get_song_path()

    def build_settings(self, settings):

        songs = load_files()
        ports = mido.get_output_names()

        jsondata = """[
                        { "type": "title",
                          "title": "LeapControl" },

                        { "type": "options",
                          "title": "PlayMode",
                          "desc": "Use Deadpan Midi or BasisMixer",
                          "section": "settings",
                          "key": "playmode",
                          "options": ["MIDI", "BM"] },

                        { "type": "options",
                          "title": "MidiPort",
                          "desc": "Select Midi Port",
                          "section": "settings",
                          "key": "midiport",
                          "options": %s },

                       { "type": "options",
                          "title": "Control",
                          "desc": "Use Mouse or LeapMotion",
                          "section": "settings",
                          "key": "control",
                          "options": ["Mouse", "LeapMotion"] },

                       { "type": "options",
                          "title": "Song",
                          "desc": "Select Song",
                          "section": "settings",
                          "key": "song",
                          "options": %s }
                    ]
                    """ % (str(ports).replace('\'', '"'),
                           str([os.path.split(song)[-1] for song in songs]).replace('\'', '"'))

        settings.add_json_panel('LeapControl', self.config, data=jsondata)

    def navigation(self):
        navigation = BoxLayout(size_hint=(1.0, 0.1))
        bt_intro = Button(text='Intro',
                          on_release=lambda a: self.screen_intro())
        bt_demo = Button(text='Demo',
                         on_release=lambda a: self.screen_demo())
        bt_replay = Button(text='Replay',
                           on_release=lambda a: self.set_screen('replay'))

        navigation.add_widget(bt_intro)
        navigation.add_widget(bt_demo)
        navigation.add_widget(bt_replay)

        return navigation

    def screen_intro(self):
        self.scm.current = 'intro'

        if self.playback_thread is not None:
            self.playback_thread.stop_playing()
        if self.knob_thread is not None:
            self.knob_thread.stop_reading()
            self.knob_thread.join()

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

        # worm
        self.worm_widget = WormWidget(self.playback_thread, self.worm_controller,
                                      size_hint=(1.0, 0.9))
        Clock.schedule_interval(self.worm_widget.update, 0.05)

        top = 0.4
        size_hint = (None, None)
        circle_layout = FloatLayout()
        bm_circle_1 = CircleWidget(pos_hint={'top': top, 'right': 0.15}, size_hint=size_hint)
        bm_circle_2 = CircleWidget(pos_hint={'top': top, 'right': 0.3}, size_hint=size_hint)
        bm_circle_3 = CircleWidget(pos_hint={'top': top, 'right': 0.45}, size_hint=size_hint)
        bm_circle_4 = CircleWidget(pos_hint={'top': top, 'right': 0.60}, size_hint=size_hint)
        bm_circle_5 = CircleWidget(pos_hint={'top': top, 'right': 0.75}, size_hint=size_hint)

        bm_scaler = Knob(pos_hint={'top': 0.4, 'right': 0.95})
        bm_scaler.value = 0
        bm_scaler.max = 100
        bm_scaler.min = 0
        bm_scaler.marker_img = "widgets/img/bline3.png"
        bm_scaler.knobimg_source = "widgets/img/knob_black.png"

        circle_layout.add_widget(bm_circle_1)
        circle_layout.add_widget(bm_circle_2)
        circle_layout.add_widget(bm_circle_3)
        circle_layout.add_widget(bm_circle_4)
        circle_layout.add_widget(bm_circle_5)
        circle_layout.add_widget(bm_scaler)

        # add widgets to layout
        screen_layout = BoxLayout(orientation='vertical')
        screen_layout.add_widget(self.worm_widget)
        screen_layout.add_widget(circle_layout)

        # add layout to screen
        demo_screen = Screen(name='demo')
        demo_screen.add_widget(screen_layout)

        # add screen to screen manager
        self.scm.add_widget(demo_screen)

        self.scm.current = 'demo'
        self.playback_thread.start()

        # if self.knob_thread is None:
        self.knob_thread = KnobThread(bm_scaler)
        self.knob_thread.start()

    def set_screen(self, screen_name):
        # self.midi_thread.stop()
        self.scm.current = screen_name

        if self.playback_thread is not None:
            self.playback_thread.stop_playing()

        if self.knob_thread is not None:
            self.knob_thread.stop_reading()
            self.knob_thread.join()

    def clear_canvas(self, obj):
        self.painter.canvas.clear()


if __name__ == '__main__':


    # if demo_type == 1:
    #     print('Using BM file as input')
    #     try:
    #         deadpan = int(input('Deadpan performance (type 1)?: '))
    #     except ValueError:
    #         deadpan = 0
    #
    #     if deadpan == 1:
    #         deadpan = True
    #     else:
    #         deadpan = False
    #
    #     # Load BM file
    #     bm_file = select_file(file_path='./bm_files', file_type='BM file')
    #
    #     # Load config file
    #     config_file = select_file(file_path='./config_files', file_type='JSON file')
    #     config = json.load(open(config_file))
    #
    #     if 'vel_min' in config:
    #         vel_min = config.pop('vel_min')
    #     else:
    #         vel_min = 30
    #
    #     if 'vel_max' in config:
    #         vel_max = config.pop('vel_max')
    #     else:
    #         vel_max = 110
    #
    #     if 'tempo_ave' in config:
    #         tempo_ave = config.pop('tempo_ave')
    #     else:
    #         # This tempo is for the Etude Op 10 No 3
    #         tempo_ave = 55
    #
    #     if 'velocity_ave' in config:
    #         velocity_ave = config.pop('velocity_ave')
    #     else:
    #         velocity_ave = 50
    #
    #     try:
    #         use_bm_controller = int(input('Use controller for the BM (type 1, default is 0)? '))
    #     except ValueError:
    #         use_bm_controller = 0
    #
    #     # Use the USB controller for scaling BM's parameters
    #     if use_bm_controller:
    #         # import powermate
    #         q_dial = queue.Queue()
    #         input_midi_ports = mido.get_input_names()
    #
    #         for cur_idx, cur_port in enumerate(input_midi_ports):
    #             print('{} \t {}'.format(cur_idx, cur_port))
    #
    #         try:
    #             port_nr = int(input('Select Port (default is 0): '))
    #         except ValueError:
    #             port_nr = 0
    #         # port_nr = int(input('Select Port: '))
    #         print('\n')
    #
    #         # bm_controller = MIDIController(input_midi_ports[port_nr],
    #         #                                q_dial)
    #         # bm_controller = threading.Thread(
    #         #     target=powermate.run_device, args=(q_dial,))
    #         # bm_controller.start()
    #     else:
    #         # bm_controller = DummyMIDIController()
    #         q_dial = None
    #
    #     playback_thread = BasisMixerMidiThread(bm_file,
    #                                            midi_port=selected_port_name,
    #                                            vel_min=vel_min,
    #                                            vel_max=vel_max,
    #                                            tempo_ave=tempo_ave,
    #                                            velocity_ave=velocity_ave,
    #                                            deadpan=deadpan,
    #                                            post_process_config=config,
    #                                            bm_queue=q_dial,
    #                                            # bm_controller=bm_controller
    #                                            )

    #run the app
    LeapControl().run()
