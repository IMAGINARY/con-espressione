"""
Run the Demo

TODO
----

* Improve user interface for setting up the demo
  (before the worm visualization?)
"""
import os
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.videoplayer import VideoPlayer
from kivy.metrics import dp

from powermate.knob_thread import (KnobThread, MidiKnobThread)
from widgets.worm import WormWidget
# from widgets.circle_vis import CircleWidget
from widgets.rect_vis import RectangleWidget

from midi_thread import MidiThread, BMThread
import controller
from kivy.config import Config
from kivy.uix.floatlayout import FloatLayout
from widgets.knob import Knob
import platform

Config.set('graphics', 'fullscreen', 0)
Config.write()


class LeapControl(App):
    def __init__(self):
        App.__init__(self)

        self.worm_controller = None
        self.playback_thread = None
        self.knob_thread = None
        self.driver = None
        self.fn_midi = None
        self.fn_video = os.path.join(os.path.dirname(__file__), 'test.mp4')
        self.config_changed = False

    def build(self):
        """Create all GUI items."""

        self.worm_controller = self.get_worm_controller()

        # basic layout blocks
        self.root = StackLayout()
        self.scm = ScreenManager(transition=SlideTransition(), size_hint=(1.0, 0.9))
        self.root.add_widget(self.scm)

        # Navigation
        # self.root.add_widget(self.navigation())

        # add screens to screen manager
        replay_screen = Screen(name='replay')
        # self.scm.add_widget(replay_screen)

        intro_screen = Screen(name='intro')
        path_video = os.path.join(self.fn_video)
        # player = VideoPlayer(source=path_video)
        # intro_screen.add_widget(player)
        # self.scm.add_widget(intro_screen)
        # self.scm.current = 'intro'
        # directly jump to demo screen
        self.screen_demo()

        return self.root

    def build_config(self, config):
        """Define default config."""

        config.setdefaults('settings', {
            'playmode': 'BM',
            'driver': 'alsa' if platform.system() == 'Linux' else 'coreaudio',
            'control': 'Mouse',
            'song': 'bach.mid',
            'bm_file': 'beethoven_op027_no2_mv1_bm_z.txt',
            'bm_config': 'beethoven_op027_no2_mv1_bm_z.json',
            'knob_type': 'PowerMate'
        })

    def on_config_change(self, config, section, key, value):
        """Invoke reset when changing config."""
        if section == "settings":
            if key == "driver":
                self.driver = value
            if key == 'control':
                self.worm_controller = self.get_worm_controller()

            self.config_changed = True

    def close_settings(self, *largs):
        super(LeapControl, self).close_settings(*largs)
        if self.scm.current == 'demo' and self.config_changed:
            self.reset_demo_threads()
            self.screen_demo()
        self.config_changed = False

    def get_worm_controller(self):
        worm_controller = controller.Mouse()
        if self.config.get('settings', 'control') == 'LeapMotion':
            # check if leap motion tracker is available
            worm_controller = controller.LeapMotion()
        return worm_controller

    def get_song_path(self):
        return os.path.join('./midi/', self.config.get('settings', 'song'))

    def get_bm_file_path(self):
        return os.path.join('./bm_files/', self.config.get('settings', 'bm_file'))

    def get_audio_driver(self):
        return self.config.get('settings', 'driver')

    def list_files(self, file_path='./midi/', file_ending='.mid'):
        """Get list of available songs."""

        all_files = [f for f in os.listdir(
            file_path) if os.path.isfile(os.path.join(file_path, f))]

        files = []

        for i, file in enumerate(all_files):
            if file.endswith(file_ending):
                files.append(os.path.join(file_path, file))

        return files

    def reset_demo_threads(self):
        if self.playback_thread is not None:
            self.playback_thread.stop_playing()
        if self.knob_thread is not None:
            self.knob_thread.stop_reading()
            self.knob_thread.join()

    def build_settings(self, settings):
        songs = self.list_files()
        bm_files = self.list_files(file_path='./bm_files/', file_ending='.txt')
        self.settings = settings

        jsondata = """[
                        { "type": "title",
                          "title": "General Options" },

                        { "type": "options",
                          "title": "Play Mode",
                          "desc": "Use Deadpan Midi or BasisMixer",
                          "section": "settings",
                          "key": "playmode",
                          "options": ["MIDI", "BM"] },

                        { "type": "options",
                          "title": "Audio Driver",
                          "desc": "Select Audio Driver",
                          "section": "settings",
                          "key": "driver",
                          "options": ["alsa", "coreaudio"] },

                       { "type": "options",
                          "title": "Control",
                          "desc": "Use Mouse or LeapMotion",
                          "section": "settings",
                          "key": "control",
                          "options": ["Mouse", "LeapMotion"] },
                       { "type": "title",
                          "title": "Midi Options" },
                       { "type": "options",
                          "title": "Song",
                          "desc": "Select Song",
                          "section": "settings",
                          "key": "song",
                          "options": %s },

                       { "type": "title",
                          "title": "BM Options" },
                       { "type": "options",
                          "title": "BM File",
                          "desc": "Select Song for the Basis Mixer",
                          "section": "settings",
                          "key": "bm_file",
                          "options": %s },

                       { "type":"title",
                         "title": "Knob Control"},
                       { "type": "options",
                         "title": "Knob Device",
                         "desc": "Use PowerMate or nanoKONTROL 2",
                         "key": "knob_type",
                         "section": "settings",
                         "options": ["PowerMate", "nanoKONTROL 2"]
                       }

                    ]
                    """ % (str([os.path.split(song)[-1] for song in songs]).replace('\'', '"'),
                           str([os.path.split(f)[-1] for f in bm_files]).replace('\'', '"'))

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
        self.reset_demo_threads()

    def screen_demo(self):
        # This is a hack
        # We rebuild the demo screen when called
        # to reset the playback.
        for cur_screen in self.scm.screens:
            if cur_screen.name == 'demo':
                # delete old demo screen
                self.scm.remove_widget(cur_screen)
                break

        # visualization
        top = 1.2
        size_hint = (None, None)
        circle_size = (dp(100), dp(100))

        rect_size = (dp(75), dp(100))
        circle_layout = FloatLayout(size_hint=(1, 0.2))
        # bm_circle_1 = CircleWidget(color=(98/255, 56/255, 101/255), pos_hint={'top': top, 'right': 0.15},
        #                            size_hint=size_hint, size=circle_size)
        # bm_circle_2 = CircleWidget(color=(87/255, 145/255, 58/255), pos_hint={'top': top, 'right': 0.3},
        #                            size_hint=size_hint, size=circle_size)
        # bm_circle_3 = CircleWidget(color=(225/255, 155/255, 21/255), pos_hint={'top': top, 'right': 0.45},
        #                            size_hint=size_hint, size=circle_size)
        # bm_circle_4 = CircleWidget(color=(35/255, 140/255, 17/2552), pos_hint={'top': top, 'right': 0.60},
        #                            size_hint=size_hint, size=circle_size)
        # bm_circle_5 = CircleWidget(color=(208/255, 8/255, 124/255), pos_hint={'top': top, 'right': 0.75},
        #                            size_hint=size_hint, size=circle_size)

        bm_circle_1 = RectangleWidget(name='Loudness', color=(98/255, 56/255, 101/255),
                                      pos_hint={'top': top, 'right': 0.15}, size_hint=size_hint, size=rect_size)
        bm_circle_2 = RectangleWidget(name='Dynamic Spread', color=(87/255, 145/255, 58/255),
                                      pos_hint={'top': top, 'right': 0.3}, size_hint=size_hint, size=rect_size)
        bm_circle_3 = RectangleWidget(name='Tempo', color=(225/255, 155/255, 21/255),
                                      pos_hint={'top': top, 'right': 0.45}, size_hint=size_hint, size=rect_size)
        bm_circle_4 = RectangleWidget(name='Microtiming', color=(35/255, 140/255, 17/2552),
                                      pos_hint={'top': top, 'right': 0.60}, size_hint=size_hint, size=rect_size)
        bm_circle_5 = RectangleWidget(name='Articulation', color=(208/255, 8/255, 124/255),
                                      pos_hint={'top': top, 'right': 0.75}, size_hint=size_hint, size=rect_size)

        bm_scaler_knob = Knob(pos_hint={'top': top, 'right': 0.95}, size=circle_size)
        bm_scaler_knob.value = 0
        bm_scaler_knob.max = 100
        bm_scaler_knob.min = 0
        bm_scaler_knob.marker_img = 'widgets/img/bline3.png'
        bm_scaler_knob.knobimg_source = 'widgets/img/knob_black.png'

        circle_layout.add_widget(bm_circle_1)
        circle_layout.add_widget(bm_circle_2)
        circle_layout.add_widget(bm_circle_3)
        circle_layout.add_widget(bm_circle_4)
        circle_layout.add_widget(bm_circle_5)
        circle_layout.add_widget(bm_scaler_knob)

        # if self.knob_thread is None:
        if self.config.get('settings', 'knob_type') == 'PowerMate':
            self.knob_thread = KnobThread(bm_scaler_knob)
        elif self.config.get('settings', 'knob_type') == 'nanoKONTROL 2':
            self.knob_thread = MidiKnobThread(bm_scaler_knob)
        self.knob_thread.start()
        self.driver = self.get_audio_driver()
        # select playback mode
        if self.config.get('settings', 'playmode') == 'MIDI':
            self.playback_thread = MidiThread(
                self.get_song_path(), self.driver)
        if self.config.get('settings', 'playmode') == 'BM':

            self.playback_thread = BMThread(self.get_bm_file_path(),
                                            driver=self.driver,
                                            scaler=bm_scaler_knob,
                                            vis=[bm_circle_1, bm_circle_2, bm_circle_3,
                                                 bm_circle_4, bm_circle_5])

        self.playback_thread.daemon = True

        # worm
        self.worm_widget = WormWidget(self.playback_thread, self.worm_controller,
                                      pos_offset=100 if self.config['settings']['playmode'] == 'BM' else 0,
                                      size_hint=(1.0, 0.8))
        Clock.schedule_interval(self.worm_widget.update, 0.05)

        self.playback_thread.start()

        # add widgets to layout
        screen_layout = BoxLayout(orientation='vertical')
        screen_layout.add_widget(self.worm_widget)

        if self.config['settings']['playmode'] == 'BM':
            screen_layout.add_widget(circle_layout)

        # add layout to screen
        demo_screen = Screen(name='demo')
        demo_screen.add_widget(screen_layout)

        # add screen to screen manager
        self.scm.add_widget(demo_screen)

        self.scm.current = 'demo'

    def set_screen(self, screen_name):
        self.scm.current = screen_name
        self.reset_demo_threads()


if __name__ == '__main__':
    # run the app
    LeapControl().run()
