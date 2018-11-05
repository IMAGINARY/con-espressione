"""
    Threading class for MIDI playback.

TODO
----
* Move decoding procedure to basismixer.performance_codec to make
BasisMixerMidiThread more modular.
* Add melody lead.
"""
import threading
import time
import mido
import numpy as np

from mido import Message
import queue as Queue
# import multiprocessing as mp

from basismixer.performance_codec import load_bm_preds
import fluidsynth


class MidiThread(threading.Thread):
    def __init__(self, midi_path, driver='alsa'):
        threading.Thread.__init__(self)
        self.path_midi = midi_path
        self.midi = None
        self.load_midi(self.path_midi)
        self.driver = driver
        self.vel_factor = 1
        self.tempo = 1
        self.play = True

    def load_midi(self, path_midi):
        self.midi = mido.MidiFile(path_midi)

    def start_playing(self):
        self.play = True

    def stop_playing(self):
        self.play = False

    def set_velocity(self, vel_factor):
        self.vel_factor = vel_factor

    def set_tempo(self, tempo):
        self.tempo = tempo

    def run(self):

        fs = fluidsynth.Synth()
        fs.start(driver=self.driver)
        sfid = fs.sfload('./sound_font/grand-piano-YDP-20160804.sf2')
        fs.program_select(0, sfid, 0, 0)

        for msg in self.midi:
            play_msg = msg
            time.sleep(play_msg.time * self.tempo)
            if msg.type == 'note_on':
                if msg.velocity != 0:
                    new_vel = int(min(msg.velocity * self.vel_factor, 127))
                    play_msg = msg.copy(velocity=new_vel)

                fs.noteon(0, play_msg.note, play_msg.velocity)

            # does not seem to be necessary
            # if msg.type == 'note_on' and msg.velocity == 0:
            #     fs.noteoff(0, play_msg.note)

            if not self.play:
                break

        fs.delete()

        return 0


class BMThread(threading.Thread):
    def __init__(self, bm_precomputed_path, driver,
                 vel_min=30, vel_max=110,
                 tempo_ave=55,
                 velocity_ave=50,
                 deadpan=False,
                 post_process_config={},
                 scaler=None, vis=None):
        threading.Thread.__init__(self)

        self.driver = driver
        self.vel = 64
        self.tempo = 1
        # Construct score-performance dictionary
        self.score_dict = load_bm_preds(bm_precomputed_path,
                                        deadpan=deadpan,
                                        post_process_config=post_process_config)
        self.tempo_ave = 60.0 / float(tempo_ave)

        # Minimal and maximal MIDI velocities allowed for each note
        self.vel_min = vel_min
        self.vel_max = vel_max

        # Controller for the effect of the BM (PowerMate)
        self.scaler = scaler
        # print(self.scaler.value)
        self.vis = vis

    def set_velocity(self, vel):
        self.vel = vel

    def set_tempo(self, tempo):
        # Scale average tempo
        self.tempo = tempo * self.tempo_ave

    def set_scaler(self, scalar):
        self.scalar = scalar

    def run(self):
        # Get unique score positions (and sort them)
        unique_onsets = np.array(list(self.score_dict.keys()))
        unique_onsets.sort()

        # Initialize playback after 0.5 seconds
        prev_eq_onset = 0.5

        # Initial time
        init_time = time.time()

        # Initialize list for note off messages
        off_messages = []

        # Initialize controller scaling
        controller_p = 1.0

        fs = fluidsynth.Synth()
        fs.start(driver=self.driver)
        sfid = fs.sfload('./sound_font/grand-piano-YDP-20160804.sf2')
        fs.program_select(0, sfid, 0, 0)

        p_update = None

        # iterate over score positions
        for on in unique_onsets:

            # Get score and performance info
            (pitch, ioi, dur,
             vt, vd, lbpr,
             tim, lart, mel) = self.score_dict[on]

            # update tempo and dynamics from the controller
            bpr_a = self.tempo
            vel_a = self.vel

            p_update = self.scaler.value

            if p_update is not None:
                controller_p = 3 * p_update / 100

            # Scale parameters
            vt = vt ** controller_p
            vd *= controller_p
            lbpr *= controller_p
            tim *= controller_p
            lart *= controller_p

            if self.vis is not None:
                for vis, scale in zip(self.vis, [vt, vd, lbpr, tim, lart]):
                    vis.update_widget(scale)

            # Compute equivalent onset
            bp = (2 ** lbpr) * bpr_a
            eq_onset = prev_eq_onset + bp * ioi

            # Compute onset for all notes in the current score position
            perf_onset = eq_onset + tim

            if np.any(perf_onset < prev_eq_onset):
                print('prob onset')
                prob_idx = np.where(perf_onset < prev_eq_onset)[0]
                perf_onset[prob_idx] = eq_onset

            # Update previous equivalent onset
            prev_eq_onset = eq_onset

            # indices of the notes in the score position according to
            # their onset
            perf_onset_idx = np.argsort(perf_onset)

            # Sort performed onsets
            perf_onset = perf_onset[perf_onset_idx]

            # Sort pitch
            pitch = pitch[perf_onset_idx]
            # Compute performed duration for each note (and sort them)
            perf_duration = ((2 ** lart) * bp * dur)[perf_onset_idx]

            # Compute performed MIDI velocity for each note (and sort them)
            perf_vel = np.clip(np.round((vt * vel_a + vd)),
                               self.vel_min,
                               self.vel_max).astype(np.int)[perf_onset_idx]

            # Initialize list of note on messages
            on_messages = []

            for p, o, d, v in zip(pitch, perf_onset,
                                  perf_duration, perf_vel):

                # Create note on message (the time attribute corresponds to
                # the time since the beginning of the piece, not the time
                # since the previous message)
                on_msg = Message('note_on', velocity=v, note=p, time=o)

                # Create note off message (the time attribute corresponds
                # to the time since the beginning of the piece)
                off_msg = Message('note_off', velocity=v, note=p, time=o+d)

                # Append the messages to their corresponding lists
                on_messages.append(on_msg)
                off_messages.append(off_msg)

            # Sort list of note off messages by offset time
            off_messages.sort(key=lambda x: x.time)

            # Send otuput MIDI messages
            while len(on_messages) > 0:

                # Send note on messages
                # Get current time
                current_time = time.time() - init_time
                if current_time >= on_messages[0].time:
                    # Send current note on message
                    fs.noteon(0, on_messages[0].note, on_messages[0].velocity)
                    # delete note on message from the list
                    del on_messages[0]

                # If there are note off messages, send them
                if len(off_messages) > 0:
                    # Update current time
                    current_time = time.time() - init_time
                    if current_time >= off_messages[0].time:
                        # Send current note off message
                        fs.noteoff(0, off_messages[0].note)
                        # delete note off message from the list
                        del off_messages[0]

                # sleep for a little bit...
                time.sleep(5e-4)

        # Send remaining note off messages
        while len(off_messages) > 0:
            current_time = time.time() - init_time
            if current_time >= off_messages[0].time:
                fs.noteoff(0, off_messages[0].note)
                del off_messages[0]

        fs.delete()
