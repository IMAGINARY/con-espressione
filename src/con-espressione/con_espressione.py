"""
    Run the Demo
"""
import argparse
import logging
import mido
import json
import numpy as np
from importlib.resources import files as resource_files

from .bm_thread import BMThread
from . import bm_files

SONG_LIST = [
    'beethoven_op027_no2_mv1_bm_z',
    'chopin_op10_No3_v422',
    'mozart_kv545_mv2',
    'beethoven_fuer_elise_complete',
]

def read_json(posix_path):
    with open(posix_path) as f:
        return json.load(f)

def read_np_array(posix_path):
    with open(posix_path) as f:
        return np.loadtxt(f)

def load_internal_song(id):
    # Import song data from internal files relative to this module

    traversable_resource_files = resource_files(bm_files)

    config_path = traversable_resource_files / f'{id}.json'
    config = read_json(config_path)

    bm_data_path = traversable_resource_files / f'{id}.txt'
    bm_data = read_np_array(bm_data_path)

    pedal_path = traversable_resource_files / f'{id}.pedal'
    pedal = np.loadtxt(pedal_path)

    return { "config": config, "bm_data": bm_data, "pedal": pedal }


class LeapControl():
    def __init__(self, songs):
        self.midi_outport = mido.open_output('con-espressione', virtual=True)
        self.midi_inport = mido.open_input('con-espressione', virtual=True)

        self.songs = songs
        self.cur_song_id = 0
        self.cur_song = self.songs[self.cur_song_id]

        # This buffer is introduced to keep the last midi messages from the GUI
        # When switching tracks, we want to keep the latest state of the GUI.
        self.message_buffer = {'tempo': 1.0, 'scaler': 0.5, 'vel': 50}

        # init playback thread
        self.playback_thread = None

    def select_song(self, val):
        # terminate playback thread if running
        if self.playback_thread is not None:
            self.stop()

        song_id = int(val)

        if val < len(self.songs):
            self.cur_song_id = song_id
            self.cur_song = self.songs[song_id]

    def play(self):
        # terminate playback thread if running
        if self.playback_thread is not None:
            self.stop()

        # init playback thread
        cur_config = self.cur_song['config']
        bm_data = self.cur_song['bm_data']
        pedal = self.cur_song['pedal']
        self.playback_thread = BMThread(cur_config,
                                        bm_data,
                                        midi_out=self.midi_outport,
                                        pedal = pedal,
                                        vel_min=cur_config['vel_min'],
                                        vel_max=cur_config['vel_max'],
                                        tempo_ave=cur_config['tempo_ave'],
                                        velocity_ave=cur_config['velocity_ave'],
                                        max_scaler=cur_config['max_scaler'],
                                        pedal_threshold=cur_config['pedal_threshold'],
                                        mel_lead_exag_coeff=cur_config['pedal_threshold'])
        self.set_tempo(self.message_buffer['tempo'])
        self.set_ml_scaler(self.message_buffer['scaler'])
        self.set_velocity(self.message_buffer['vel'])
        self.playback_thread.start_playing()
        self.playback_thread.start()

    def stop(self):
        if self.playback_thread is not None:
            self.playback_thread.stop_playing()
            self.playback_thread.join()

    def set_velocity(self, val):
        # store latest message
        self.message_buffer['vel'] = val

        # scale value in [0, 127] to [0.5, 2]
        if val <= 64:
            out = (0.5 / 64.0) * val + 0.5
        if val > 64:
            out = (2.0 / 127.0) * val

        if self.playback_thread is not None:
            self.playback_thread.set_velocity(out)

    def set_tempo(self, val):
        # store latest message
        self.message_buffer['tempo'] = val

        # scale value in [0, 127] to [0.5, 2]
        cur_config = self.cur_song['config']
        if val <= 64:
            out = ((1 - cur_config['tempo_rel_min']) / 64.0) * val + cur_config['tempo_rel_min']
        if val > 64:
            out = ((cur_config['tempo_rel_max'] - 1) / 64.0) * (val - 64) + 1

        if self.playback_thread is not None:
            self.playback_thread.set_tempo(out)

    def set_ml_scaler(self, val):
        # store latest message
        self.message_buffer['scaler'] = val

        # scale value in [0, 127] to [0, 100]
        out = (100 / 127) * val

        if self.playback_thread is not None:
            self.playback_thread.set_scaler(out)

    def parse_midi_msg(self, msg):
        if msg.type == 'song_select':
            # select song
            logging.debug('Received Song change. New value: {}'.format(msg.song))
            self.select_song(int(msg.song))
        if msg.type == 'control_change':
            if msg.channel == 0:
                if msg.control == 20:
                    # tempo
                    self.set_tempo(float(msg.value))
                if msg.control == 21:
                    # velocity
                    self.set_velocity(float(msg.value))
                if msg.control == 22:
                    # ml-scaler
                    self.set_ml_scaler(float(msg.value))
                if msg.control == 24:
                    # start playing
                    logging.debug('Received Play command. New value: {}'.format(msg.value))
                    if int(msg.value) == 127:
                        self.play()
                if msg.control == 25:
                    # stop playing
                    logging.debug('Received Stop command. New value: {}'.format(msg.value))
                    if int(msg.value) == 127:
                        self.stop()


def main():
    songs = list(map(load_internal_song, SONG_LIST))

    # instantiate LeapControl
    lc = LeapControl(songs)

    try:
        # listen to input MIDI port for messages
        for msg in lc.midi_inport:
            lc.parse_midi_msg(msg)
    except AttributeError as e:
        print('Received unrecognized MIDI message.')
        print(e)
    except KeyboardInterrupt:
        print('Received keyboard interrupt. Shutting down...')
    finally:
        # clean-up
        lc.stop()
        if lc.playback_thread is not None:
            lc.playback_thread.join()
        lc.midi_outport.close()
        lc.midi_inport.close()


def main_cli():
    parser = argparse.ArgumentParser(description='Backend for BM-Application.')
    parser.add_argument('--verbose', help='Print Debug logs.', action='store_true')
    args = parser.parse_args()

    # set logging level
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # start backend
    main()
