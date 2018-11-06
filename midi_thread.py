"""
    Threading class for MIDI playback.

TODO
----
* Merge BMThread and MidiThread
"""
import threading
import time
import mido
import numpy as np

# from mido import Message
# import queue as Queue
# import multiprocessing as mp

from basismixer.performance_codec import load_bm_preds, PerformanceCodec


class MidiThread(threading.Thread):
    def __init__(self, midi_path, midi_port):
        threading.Thread.__init__(self)
        self.path_midi = midi_path
        self.midi = None
        self.load_midi(self.path_midi)
        self.midi_port = midi_port
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
        outport = mido.open_output(self.midi_port)

        for msg in self.midi:
            play_msg = msg
            if msg.type == 'note_on':
                if msg.velocity != 0:
                    new_vel = int(min(msg.velocity * self.vel_factor, 127))

                    play_msg = msg.copy(velocity=new_vel)

            time.sleep(play_msg.time*self.tempo)
            outport.send(play_msg)

            if not self.play:
                break

        return 0


class BMThread(threading.Thread):
    def __init__(self, bm_precomputed_path, midi_port,
                 vel_min=30, vel_max=110,
                 tempo_ave=55,
                 velocity_ave=50,
                 deadpan=False,
                 post_process_config={},
                 scaler=None, vis=None,
                 max_scaler=3.0):
        threading.Thread.__init__(self)

        self.midi_port = midi_port
        self.vel = 64
        self.tempo = 1
        # Construct score-performance dictionary
        self.score_dict = load_bm_preds(bm_precomputed_path,
                                        deadpan=deadpan,
                                        post_process_config=post_process_config)

        self.tempo_ave = post_process_config.get('tempo_ave', 60.0 / float(tempo_ave))

        # Minimal and maximal MIDI velocities allowed for each note
        self.vel_min = post_process_config.get('vel_min', vel_min)
        self.vel_max = post_process_config.get('vel_max', vel_max)

        # Controller for the effect of the BM (PowerMate)
        self.scaler = scaler
        print(self.scaler.value)
        self.max_scaler = max_scaler
        self.vis = vis
        self.pc = PerformanceCodec(tempo_ave=tempo_ave,
                                   velocity_ave=velocity_ave,
                                   init_eq_onset=0.5,
                                   vel_min=vel_min,
                                   vel_max=vel_max)

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

        # Initial time
        init_time = time.time()

        # Initialize list for note off messages
        off_messages = []

        # Initialize controller scaling
        controller_p = 1.0

        p_update = None
        # Open port
        with mido.open_output(self.midi_port) as outport:

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
                    controller_p = self.max_scaler * p_update / 100

                # Scale parameters
                vt = vt ** controller_p
                vd *= controller_p
                lbpr *= controller_p
                tim *= controller_p
                lart *= controller_p

                if self.vis is not None:
                    for vis, scale in zip(self.vis, [vt, vd, lbpr, tim, lart]):
                        vis.update_widget(scale)

                # Decode parameters to MIDI messages
                on_messages, _off_messages = self.pc.decode_online(
                    pitch=pitch, ioi=ioi, dur=dur, vt=vt,
                    vd=vd, lbpr=lbpr, tim=tim, lart=lart,
                    mel=mel, bpr_a=bpr_a, vel_a=vel_a)

                off_messages += _off_messages

                # Sort list of note off messages by offset time
                off_messages.sort(key=lambda x: x.time)

                # Send otuput MIDI messages
                while len(on_messages) > 0:

                    # Send note on messages
                    # Get current time
                    current_time = time.time() - init_time
                    if current_time >= on_messages[0].time:
                        # Send current note on message
                        outport.send(on_messages[0])
                        # delete note on message from the list
                        del on_messages[0]

                    # If there are note off messages, send them
                    if len(off_messages) > 0:
                        # Update current time
                        current_time = time.time() - init_time
                        if current_time >= off_messages[0].time:
                            # Send current note off message
                            outport.send(off_messages[0])
                            # delete note off message from the list
                            del off_messages[0]

                    # sleep for a little bit...
                    time.sleep(5e-4)

            # Send remaining note off messages
            while len(off_messages) > 0:
                current_time = time.time() - init_time
                if current_time >= off_messages[0].time:
                    outport.send(off_messages[0])
                    del off_messages[0]
