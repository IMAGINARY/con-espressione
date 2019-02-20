"""
    Run the Demo
"""
import os
import mido
from powermate.knob_thread import (KnobThread, MidiKnobThread)
from midi_thread import MidiThread, BMThread
import platform


class LeapControl():
    def __init__(self, midi_out, config):
        self.midi_outport = midi_out
        self.playback_thread = BMThread(config['bm_file'], midi_out=self.midi_outport)

        # init tempo and velocity
        self.playback_thread.set_tempo(1.0)
        self.playback_thread.set_scaler(0.0)
        self.playback_thread.set_velocity(50.0)

    def select_song(self):
        # TODO
        pass

    def play(self):
        self.playback_thread.start()

    def stop(self):
        self.playback_thread.stop_playing()

    def set_velocity(self, val):
        # scale value in [0, 127] to [0.5, 2]
        if val <= 64:
            out = (0.5 / 64.0) * val + 0.5
        if val > 64:
            out = (2.0 / 127.0) * val

        self.playback_thread.set_velocity(out)

    def set_tempo(self, val):
        # scale value in [0, 127] to [0.5, 2]
        if val <= 64:
            out = - (2.0 / 128.0) * val + 2.0
        if val > 64:
            out = - (1.0 / 127.0) * val + 1.5

        self.playback_thread.set_tempo(out)

    def set_ml_scaler(self, val):
        # scale value in [0, 127] to [0, 100]
        out = (100 / 127) * val

        self.playback_thread.set_scaler(out)


def main():
    CONFIG = {'playmode': 'BM',
              'driver': 'alsa' if platform.system() == 'Linux' else 'coreaudio',
              'control': 'Mouse',
              'song': 'bach.mid',
              'bm_file': 'bm_files/beethoven_op027_no2_mv1_bm_z.txt',
              'bm_config': 'bm_files/beethoven_op027_no2_mv1_bm_z.json',
              'knob_type': 'PowerMate'}

    midi_lc_out = mido.open_output('LeapControl', virtual=True)

    try:
        # instantiate LeapControl
        lc = LeapControl(midi_lc_out, CONFIG)

        # listen to MIDI port for Control Changes
        with mido.open_input('LeapControl', virtual=True) as port:
            for msg in port:
                if msg.type == 'control_change':
                    if msg.channel == 0:
                        if msg.control == 20:
                            # tempo
                            lc.set_tempo(float(msg.value))
                        if msg.control == 21:
                            # velocity
                            lc.set_velocity(float(msg.value))
                        if msg.control == 22:
                            # ml-scaler
                            lc.set_ml_scaler(float(msg.value))
                        if msg.control == 23:
                            # select song
                            lc.select_song(int(msg.value))
                        if msg.control == 24:
                            # start playing
                            if int(msg.value) == 127:
                                lc.play()
                        if msg.control == 25:
                            # stop playing
                            if int(msg.value) == 127:
                                lc.stop()

    except KeyboardInterrupt:
        print('Shutting down...')
        lc.stop()
        lc.playback_thread.join()


if __name__ == '__main__':
    main()
