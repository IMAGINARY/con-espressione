import json
from midi_thread import BMThread, AsyncBasisMixer


class LeapControl():
    def __init__(self, config, song_list, midi_player):
        self.midi_player = midi_player

        self.song_list = song_list
        self.cur_song_id = 0
        self.cur_song = self.song_list[self.cur_song_id]
        self.cur_config = None

        # This buffer is introduced to keep the last midi messages from the GUI
        # When switching tracks, we want to keep the latest state of the GUI.
        self.message_buffer = {'tempo': 1.0, 'scaler': 0.5, 'vel': 50}

        # init playback thread
        self.playback_thread = None

    def load_config(self):
        path_config = self.cur_song.replace('.txt', '.json')

        with open(path_config) as json_file:
            config = json.load(json_file)

        self.cur_config = config

    def select_song(self, val):
        # terminate playback thread if running
        if self.playback_thread is not None:
            self.stop()

        val = int(val)

        if val < len(self.song_list):
            self.cur_song_id = int(val)
            self.cur_song = self.song_list[self.cur_song_id]

    async def play(self):
        # terminate playback thread if running
        if self.playback_thread is not None:
            await self.stop()

        # init playback thread
        self.load_config()
        self.playback_thread = AsyncBasisMixer(self.cur_song, midi_player=self.midi_player,
                                        vel_min=self.cur_config['vel_min'],
                                        vel_max=self.cur_config['vel_max'],
                                        tempo_ave=self.cur_config['tempo_ave'],
                                        velocity_ave=self.cur_config['velocity_ave'],
                                        max_scaler=self.cur_config['max_scaler'],
                                        pedal_threshold=self.cur_config['pedal_threshold'],
                                        mel_lead_exag_coeff=self.cur_config['pedal_threshold'])
        self.set_tempo(self.message_buffer['tempo'])
        self.set_tempo(64)
        self.set_ml_scaler(self.message_buffer['scaler'])
        self.set_velocity(self.message_buffer['vel'])
        self.playback_thread.start_playing()
        await self.playback_thread.start()

    async def stop(self):
        if self.playback_thread is not None:
            self.playback_thread.stop_playing()
            await self.playback_thread.join()

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
        if val <= 64:
            out = ((1 - self.cur_config['tempo_rel_min']) / 64.0) * val + self.cur_config['tempo_rel_min']
        if val > 64:
            out = ((self.cur_config['tempo_rel_max'] - 1) / 64.0) * (val - 64) + 1

        if self.playback_thread is not None:
            self.playback_thread.set_tempo(out)

    def set_ml_scaler(self, val):
        # store latest message
        self.message_buffer['scaler'] = val

        # scale value in [0, 127] to [0, 100]
        out = (100 / 127) * val

        if self.playback_thread is not None:
            self.playback_thread.set_scaler(out)

    async def parse_midi_msg(self, msg):
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
                        await self.play()
                if msg.control == 25:
                    # stop playing
                    logging.debug('Received Stop command. New value: {}'.format(msg.value))
                    if int(msg.value) == 127:
                        await self.stop()