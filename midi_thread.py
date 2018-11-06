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


from basismixer.performance_codec import (load_bm_preds, PerformanceCodec,
                                          get_vis_scaling_factors, compute_vis_scaling)
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
                 scaler=None, vis=None,
                 max_scaler=3.0):
        threading.Thread.__init__(self)

        self.driver = driver
        self.vel = 64
        self.tempo = 1
        # Construct score-performance dictionary
        self.score_dict = load_bm_preds(bm_precomputed_path,
                                        deadpan=deadpan,
                                        post_process_config=post_process_config)

        self.tempo_ave = post_process_config.get(
            'tempo_ave', 60.0 / float(tempo_ave))

        self.velocity_ave = post_process_config.get('velocity_ave',
                                                    velocity_ave)
        # Minimal and maximal MIDI velocities allowed for each note
        self.vel_min = post_process_config.get('vel_min', vel_min)
        self.vel_max = post_process_config.get('vel_max', vel_max)

        # Controller for the effect of the BM (PowerMate)
        self.scaler = scaler
        # print(self.scaler.value)
        self.max_scaler = max_scaler
        self.vis = vis
        self.pc = PerformanceCodec(tempo_ave=self.tempo_ave,
                                   velocity_ave=velocity_ave,
                                   init_eq_onset=0.5,
                                   vel_min=self.vel_min,
                                   vel_max=self.vel_max)
        self.vis_scaling_factors = get_vis_scaling_factors(self. score_dict,
                                                           self.max_scaler)

    def set_velocity(self, vel):
        self.vel = vel * self.velocity_ave

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
                controller_p = self.max_scaler * p_update / 100

            # Scale parameters
            vt = vt ** controller_p
            vd *= controller_p
            lbpr *= controller_p
            tim *= controller_p
            lart *= controller_p

            vts, vds, lbprs, tims, larts = compute_vis_scaling(vt, vd, lbpr, tim, lart,
                                                               self.vis_scaling_factors)
            if self.vis is not None:
                for vis, scale in zip(self.vis, [vts, vds, lbprs, tims, larts]):
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
