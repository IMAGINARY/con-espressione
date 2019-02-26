"""
    Threading class for MIDI playback.
    We distinguish between simple Midi playback in the class `MidiThread`
    and performance rendering through the Basis Mixer in class `BMThread`.
    In both cases, the outputs will be Midi events.
"""
import threading
import time
import mido
import numpy as np
import json
import mido
import os

from basismixer.performance_codec import (load_bm_preds,
                                          PerformanceCodec)
from basismixer.bm_utils import (get_vis_scaling_factors,
                                 compute_vis_scaling, sigmoid,
                                 SIGMOID_1)
from basismixer.expression_tools import scale_parameters


class MidiThread(threading.Thread):

    def __init__(self, midi_path, driver='alsa'):
        threading.Thread.__init__(self)
        self.path_midi = midi_path
        self.midi = None
        self.load_midi(self.path_midi)
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
        for msg in self.midi:
            play_msg = msg
            time.sleep(play_msg.time * self.tempo)
            if msg.type == 'note_on':
                if msg.velocity != 0:
                    new_vel = int(min(msg.velocity * self.vel_factor, 127))
                    play_msg = msg.copy(velocity=new_vel)

        return 0


class BMThread(threading.Thread):

    def __init__(self, bm_precomputed_path, midi_out,
                 vel_min=30, vel_max=110,
                 tempo_ave=55,
                 velocity_ave=50,
                 deadpan=False,
                 max_scaler=2.0,
                 pedal_threshold=60):
        threading.Thread.__init__(self)

        self.midi_outport = midi_out
        self.vel = 64
        self.tempo = 1
        self.reached_end = False

        self.post_process_config = json.load(open(bm_precomputed_path.replace('.txt', '.json')))
        pedal_fn = (bm_precomputed_path.replace('.txt', '.pedal')
                    if os.path.exists(bm_precomputed_path.replace('.txt', '.pedal'))
                    else None)

        # Construct score-performance dictionary
        self.score_dict = load_bm_preds(bm_precomputed_path,
                                        deadpan=deadpan,
                                        post_process_config=self.post_process_config,
                                        pedal_fn=pedal_fn)

        self.tempo_ave = self.post_process_config.get('tempo_ave', 60.0 / float(tempo_ave))

        self.velocity_ave = self.post_process_config.get('velocity_ave',
                                                         velocity_ave)
        # Minimal and maximal MIDI velocities allowed for each note
        self.vel_min = self.post_process_config.get('vel_min', vel_min)
        self.vel_max = self.post_process_config.get('vel_max', vel_max)
        self.pedal_threshold = self.post_process_config.get('pedal_threshold', pedal_threshold)

        # Controller for the effect of the BM
        self.scaler = None

        # Maximal amount that the scaling affects the BM parameters
        self.max_scaler = self.post_process_config.get('max_scaler', max_scaler)

        if 'vel_trend' in self.post_process_config:
            self.remove_trend_vt = self.post_process_config['vel_trend'].get('remove_trend', True)
        else:
            self.remove_trend_vt = True

        if 'log_bpr' in self.post_process_config:
            self.remove_trend_lbpr = self.post_process_config['log_bpr'].get('remove_trend', True)
        else:
            self.remove_trend_lbpr = True

        # Initialize performance codec
        self.pc = PerformanceCodec(tempo_ave=self.tempo_ave,
                                   velocity_ave=self.velocity_ave,
                                   init_eq_onset=0.5,
                                   vel_min=self.vel_min,
                                   vel_max=self.vel_max,
                                   remove_trend_vt=self.remove_trend_vt,
                                   remove_trend_lbpr=self.remove_trend_lbpr,
                                   pedal_threshold=self.pedal_threshold)

        # Scaling factors for the visualization
        self.vis_scaling_factors = get_vis_scaling_factors(self.score_dict,
                                                           self.max_scaler,
                                                           remove_trend_vt=self.remove_trend_vt)

        self.play = True

    def set_velocity(self, vel):
        self.vel = vel * self.velocity_ave

    def set_tempo(self, tempo):
        # Scale average tempo
        if tempo <= 1:
            t_scale = tempo
        if tempo > 1:
            # TODO: Test other scalings
            t_scale = sigmoid(tempo) / SIGMOID_1
        self.tempo = t_scale * self.tempo_ave

    def set_scaler(self, scaler):
        self.scaler = scaler

    def run(self):
        # Get unique score positions (and sort them)
        unique_onsets = np.array(list(self.score_dict.keys()))
        unique_onsets.sort()

        # Initial time
        init_time = time.time()

        # Initialize list for note off messages
        off_messages = []
        ped_messages = []
        currently_sounding = []

        # Initialize controller scaling
        controller_p = 1.0

        p_update = None

        # iterate over score positions
        for on in unique_onsets:

            # Get score and performance info
            (pitch, ioi, dur,
             vt, vd, lbpr,
             tim, lart, mel, ped) = self.score_dict[on]

            # update tempo and dynamics from the controller
            bpr_a = self.tempo
            vel_a = self.vel

            p_update = self.scaler

            if p_update is not None:
                controller_p = self.max_scaler * p_update / 100

            if vt is not None:
                # Scale bm parameters
                vt, vd, lbpr, tim, lart, ped, mel = scale_parameters(
                    vt=vt, vd=vd, lbpr=lbpr,
                    tim=tim, lart=lart, pitch=pitch,
                    mel=mel, ped=ped, vel_a=vel_a,
                    bpr_a=bpr_a, controller_p=controller_p,
                    remove_trend_vt=self.remove_trend_vt)

                vts, vds, lbprs, tims, larts = compute_vis_scaling(
                    vt, vd, lbpr, tim, lart, self.vis_scaling_factors)

                # Send vis information via MIDI message
                msg = mido.Message('control_change', channel=1, control=110, value=int(vts * 127))
                self.midi_outport.send(msg)
                msg = mido.Message('control_change', channel=1, control=111, value=int(vds * 127))
                self.midi_outport.send(msg)
                msg = mido.Message('control_change', channel=1, control=112, value=int(lbprs * 127))
                self.midi_outport.send(msg)
                msg = mido.Message('control_change', channel=1, control=113, value=int(tims * 127))
                self.midi_outport.send(msg)
                msg = mido.Message('control_change', channel=1, control=114, value=int(larts * 127))
                self.midi_outport.send(msg)

            # Decode parameters to MIDI messages
            on_messages, _off_messages, _ped_messages = self.pc.decode_online(
                pitch=pitch, ioi=ioi, dur=dur, vt=vt,
                vd=vd, lbpr=lbpr, tim=tim, lart=lart,
                mel=mel, bpr_a=bpr_a, vel_a=vel_a, ped=ped,
                controller_p=controller_p)

            off_messages += _off_messages
            ped_messages += _ped_messages

            # Sort list of note off messages by offset time
            off_messages.sort(key=lambda x: x.time)
            ped_messages.sort(key=lambda x: x.time)

            # Send otuput MIDI messages
            while (len(on_messages) > 0 or len(ped_messages) > 0) and self.play:
                # Send pedal
                if len(ped_messages) > 0:
                    current_time = time.time() - init_time

                    if current_time >= ped_messages[0].time:
                        msg = mido.Message('control_change', channel=0, control=64, value=ped_messages[0].value)
                        self.midi_outport.send(msg)
                        del ped_messages[0]

                # If there are note off messages, send them
                if len(off_messages) > 0:
                    # Update current time
                    current_time = time.time() - init_time

                    if current_time >= off_messages[0].time:
                        # Update list of currently sounding notes
                        if off_messages[0].note in currently_sounding:
                            csp_ix = currently_sounding.index(off_messages[0].note)
                            del currently_sounding[csp_ix]

                        # Send current note off message
                        msg = mido.Message('note_off', channel=0, note=off_messages[0].note, velocity=0)
                        self.midi_outport.send(msg)

                        # delete note off message from the list
                        del off_messages[0]

                # Send note on messages
                if len(on_messages) > 0:
                    current_time = time.time() - init_time

                    if current_time >= on_messages[0].time:
                        # Check if note is currently on and send a
                        # note off message (and update off_messages
                        # in case it is active.
                        if on_messages[0].note in currently_sounding:
                            csp_ix = currently_sounding.index(on_messages[0].note)
                            del currently_sounding[csp_ix]

                            for noi, nomsg in enumerate(off_messages):
                                if nomsg.note == on_messages[0].note:
                                    # fs.noteoff(0, on_messages[0].note)
                                    msg = mido.Message('note_off', channel=0, note=on_messages[0].note, velocity=0)
                                    self.midi_outport.send(msg)

                                    del off_messages[noi]
                                    break
                        # Send current note on message
                        msg = mido.Message('note_on', channel=0, note=on_messages[0].note, velocity=on_messages[0].velocity)
                        self.midi_outport.send(msg)
                        currently_sounding.append(on_messages[0].note)

                        # delete note on message from the list
                        del on_messages[0]

                # sleep for a little bit...
                time.sleep(5e-4)

        # Send remaining note off messages
        while len(off_messages) > 0 and self.play:
            current_time = time.time() - init_time

            if current_time >= off_messages[0].time:
                msg = mido.Message('note_off', channel=0, note=off_messages[0].note, velocity=0)
                self.midi_outport.send(msg)
                del off_messages[0]

        # send reached end signal
        self.reached_end = True
        msg = mido.Message('control_change', channel=1, control=115, value=int(127))
        self.midi_outport.send(msg)

        return self.reached_end

    def start_playing(self):
        self.play = True

    def stop_playing(self):
        # TODO: check if this is necessary in final
        # release pedal
        msg = mido.Message('control_change', channel=0, control=64, value=0)
        self.midi_outport.send(msg)

        for cur_note in range(127):
            msg = mido.Message('note_off', channel=0, note=cur_note, velocity=0)
            self.midi_outport.send(msg)

        # send all sounds off signal
        msg = mido.Message('control_change', channel=0, control=120, value=0)
        self.midi_outport.send(msg)

        # send all note off signal
        msg = mido.Message('control_change', channel=0, control=123, value=0)
        self.midi_outport.send(msg)

        # send Reset All Controllers
        msg = mido.Message('control_change', channel=0, control=121, value=0)
        self.midi_outport.send(msg)

        self.play = False
