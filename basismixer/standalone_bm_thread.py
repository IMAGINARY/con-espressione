import threading
import time
import mido
import numpy as np
import os
import json
import fluidsynth

from basismixer.performance_codec import (load_bm_preds,
                                          PerformanceCodec)

from basismixer.expression_tools import scale_parameters_w_controller

from basismixer.bm_controller import BMKnob, BMControllerThread


class OutputMIDIPort():
    def __init__(self, output_midi_port):
        # threading.Thread.__init__(self)
        self.port_name = output_midi_port
        self.midi_port = mido.open_output(self.port_name)

        self.play = True

    def send(self, msg):
        if self.play:
            self.midi_port.send(msg)
        else:
            self.midi_port.reset()

    def close(self):
        self.midi_port.reset()
        self.midi_port.close()


class OutputFSPort():
    def __init__(self, driver='coreaudio',
                 soundfont='../sound_font/grand-piano-YDP-20160804.sf2'):
        self.driver = driver
        self.soundfont = soundfont
        self.fs = fluidsynth.Synth()
        self.fs.start(driver=self.driver)
        sfid = self.fs.sfload(self.soundfont)
        self.fs.program_select(0, sfid, 0, 0)

    def send(self, msg):
        if msg.type == 'note_on':
            self.fs.noteon(0, msg.note, msg.velocity)
        elif msg.type == 'note_off':
            self.fs.noteoff(0, msg.note)
        elif msg.type == 'control_change':
            self.fs.cc(0, msg.control, msg.value)

    def close(self):
        self.fs.delete()


class BMThread(threading.Thread):

    def __init__(self, bm_precomputed_path,
                 output_port,
                 vel_min=30, vel_max=110,
                 tempo_ave=55,
                 velocity_ave=50,
                 deadpan=False,
                 bm_controller=None,
                 remove_trend_vt=False,
                 remove_trend_lbpr=False):
        threading.Thread.__init__(self)

        pedal_fn = (bm_precomputed_path.replace('.txt', '.pedal')
                    if os.path.exists(bm_precomputed_path.replace('.txt', '.pedal'))
                    else None)
        # Construct score-performance dictionary
        self.score_dict = load_bm_preds(bm_precomputed_path,
                                        deadpan=deadpan,
                                        post_process_config={},
                                        pedal_fn=pedal_fn)

        self.tempo_ave = 60.0 / float(tempo_ave)

        self.velocity_ave = velocity_ave

        # Minimal and maximal MIDI velocities allowed for each note
        self.vel_min = vel_min
        self.vel_max = vel_max

        self.remove_trend_vt = remove_trend_vt
        self.remove_trend_lbpr = remove_trend_lbpr

        # Initialize performance codec
        self.pc = PerformanceCodec(tempo_ave=self.tempo_ave,
                                   velocity_ave=velocity_ave,
                                   init_eq_onset=0.5,
                                   vel_min=self.vel_min,
                                   vel_max=self.vel_max,
                                   remove_trend_vt=self.remove_trend_vt,
                                   remove_trend_lbpr=self.remove_trend_lbpr)

        self.bm_controller = bm_controller
        if self.bm_controller is not None:
            self.bm_controller.daemon = True

        self.play = True

        self.output_port = output_port

    def run(self):

        if self.bm_controller is not None:
            self.bm_controller.start()
        # Get unique score positions (and sort them)
        unique_onsets = np.array(list(self.score_dict.keys()))
        unique_onsets.sort()

        # Initial time
        init_time = time.time()

        # Initialize list for note off messages
        off_messages = []
        ped_messages = []
        currently_sounding = []

        # iterate over score positions
        for on in unique_onsets:

            # Get score and performance info
            (pitch, ioi, dur,
             vt, vd, lbpr,
             tim, lart, mel, ped) = self.score_dict[on]

            # update tempo and dynamics from the controller
            bpr_a = self.tempo_ave
            vel_a = self.velocity_ave

            if vt is not None:
                # Scale bm parameters
                vt, vd, lbpr, tim, lart, ped, mel = scale_parameters_w_controller(
                    vt=vt, vd=vd, lbpr=lbpr,
                    tim=tim, lart=lart, pitch=pitch,
                    mel=mel, ped=ped,
                    bm_controller=self.bm_controller,
                    vel_a=vel_a,
                    bpr_a=bpr_a,
                    remove_trend_vt=self.remove_trend_vt,
                    remove_trend_lbpr=self.remove_trend_lbpr)

            # Decode parameters to MIDI messages
            on_messages, _off_messages, _ped_messages = self.pc.decode_online(
                pitch=pitch, ioi=ioi, dur=dur, vt=vt,
                vd=vd, lbpr=lbpr, tim=tim, lart=lart,
                mel=mel, bpr_a=bpr_a, vel_a=vel_a, ped=ped)

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
                        self.output_port.send(ped_messages[0])
                        del ped_messages[0]

                # If there are note off messages, send them
                if len(off_messages) > 0:
                    # Update current time
                    current_time = time.time() - init_time
                    if current_time >= off_messages[0].time:
                        # Update list of currently sounding notes
                        if off_messages[0].note in currently_sounding:
                            csp_ix = currently_sounding.index(
                                off_messages[0].note)
                            del currently_sounding[csp_ix]
                        # Send current note off message
                        self.output_port.send(off_messages[0])
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
                            csp_ix = currently_sounding.index(
                                on_messages[0].note)
                            del currently_sounding[csp_ix]
                            for noi, nomsg in enumerate(off_messages):
                                if nomsg.note == on_messages[0].note:
                                    self.output_port.send(off_messages[noi])
                                    del off_messages[noi]
                                    break
                        # Send current note on message
                        self.output_port.send(on_messages[0])
                        currently_sounding.append(on_messages[0].note)
                        # delete note on message from the list
                        del on_messages[0]

                # sleep for a little bit...
                time.sleep(5e-4)

            if not self.play:
                break

        # Send remaining note off messages
        while len(off_messages) > 0 and self.play:
            current_time = time.time() - init_time
            if current_time >= off_messages[0].time:
                self.output_port.send(off_messages[0])
                del off_messages[0]

        self.output_port.close()

    def start_playing(self):
        self.play = True

    def stop_playing(self):
        self.play = False


if __name__ == '__main__':

    output_ports = mido.get_output_names()
    print(output_ports)
    # outport_nr = input()
    # outport = OutputMIDIPort(output_ports[0])
    outport = OutputFSPort()
    fn = '../bm_files/beethoven_op027_no2_mv1_bm_of_wm.txt'
    config = fn.replace('.txt', '.json')

    config = json.load(open(config))

    vt_mean = BMKnob(min_value=25, max_value=90,
                     init_value=config['velocity_ave'],
                     name='vt_mean')
    vt_std = BMKnob(min_value=1, max_value=10)
    vd_mean = BMKnob(min_value=-30, max_value=30,
                     init_value=config['vel_dev']['mean'],
                     name='vd_mean')
    vd_std = BMKnob(min_value=1, max_value=5,
                    init_value=config['vel_dev']['std'],
                    name='vd_std')
    lbpr_mean = BMKnob(min_value=-2, max_value=2,
                       init_value=config['log_bpr']['mean'],
                       name='lbpr_mean')
    lbpr_std = BMKnob(min_value=0.1, max_value=2,
                      init_value=config['log_bpr']['std'],
                      name='lbpr_std')
    tim_mean = BMKnob(min_value=-0.1, max_value=0.1,
                      init_value=config['timing']['mean'],
                      name='tim_mean')
    tim_std = BMKnob(min_value=0.01, max_value=0.05,
                     init_value=config['timing']['std'],
                     name='tim_std')
    lart_mean = BMKnob(min_value=-3, max_value=3,
                       init_value=config['log_art']['mean'],
                       name='lart_mean')
    lart_std = BMKnob(min_value=0.1, max_value=3,
                      init_value=config['log_art']['std'],
                      name='lart_std')

    bc = BMControllerThread(vt_mean=vt_mean,
                            vt_std=vt_std,
                            vd_mean=vd_mean,
                            vd_std=vd_std,
                            lbpr_mean=lbpr_mean,
                            lbpr_std=lbpr_std,
                            tim_mean=tim_mean,
                            tim_std=tim_std,
                            lart_mean=lart_mean,
                            lart_std=lart_std)

    bmt = BMThread(fn,
                   output_port=outport,
                   vel_min=config['vel_min'],
                   vel_max=config['vel_max'],
                   velocity_ave=config['velocity_ave'],
                   tempo_ave=60.0/config['tempo_ave'],
                   bm_controller=bc)
    bmt.daemon = True
    bmt.start()

    try:
        while True:
            outconfig = '/tmp/config.json'
            out_config = bc.dump_config()
            out_config['vel_min'] = config['vel_min']
            out_config['vel_max'] = config['vel_max']
            out_config['velocity_ave'] = config['velocity_ave']
            out_config['tempo_ave'] = config['tempo_ave']
            with open(outconfig, 'w') as f:
                json.dump(out_config, f, indent=4)

            time.sleep(0.5)

    except KeyboardInterrupt:
        pass
