"""
    Run the Demo
"""
import os
import mido
from powermate.knob_thread import (KnobThread, MidiKnobThread)
from midi_thread import MidiThread, BMThread
import platform


class LeapControl():
    def __init__(self, config):
        self.playback_thread = BMThread(config['bm_file'], driver=config['driver'])
        self.playback_thread.set_tempo(1.0)
        self.playback_thread.set_velocity(1.0)

    def select_song(self):
        pass

    def play(self):
        self.playback_thread.start()

    def stop(self):
        pass

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


def main():
    CONFIG = {'playmode': 'BM',
              'driver': 'alsa' if platform.system() == 'Linux' else 'coreaudio',
              'control': 'Mouse',
              'song': 'bach.mid',
              'bm_file': 'bm_files/beethoven_op027_no2_mv1_bm_z.txt',
              'bm_config': 'bm_files/beethoven_op027_no2_mv1_bm_z.json',
              'knob_type': 'PowerMate'}

    # instantiate LeapControl
    lc = LeapControl(CONFIG)
    lc.play()

    # midi_lc_in = mido.open_input('LeapControl-In', virtual=True)
    # midi_lc_out = mido.open_output('LeapControl-Out', virtual=True)

    # listen to MIDI port for Control Changes
    with mido.open_input('LeapControl-In', virtual=True) as port:
        for msg in port:
            if msg.type == 'control_change':
                if msg.channel == 0:
                    if msg.control == 1:
                        # tempo
                        lc.set_tempo(float(msg.value))
                    if msg.control == 2:
                        # velocity
                        lc.set_velocity(float(msg.value))


if __name__ == '__main__':
    main()
