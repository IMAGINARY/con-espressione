"""
Tests for performance generation using the precomputed inputs of the
Basis Mixer.
"""
import mido
import numpy as np
import time

from mido import Message

from basismixer.performance_codec import (load_bm_preds,
                                          compute_dummy_preds_from_midi)


class DummyController(object):

    tempo = 60
    velocity = 64


def test_dummy_performance_generation():

    # Select MIDI port
    midi_ports = mido.get_output_names()

    for cur_idx, cur_port in enumerate(midi_ports):
        print('{} \t {}'.format(cur_idx, cur_port))

    port_nr = int(input('Select Port: '))

    selected_port_name = midi_ports[port_nr]

    # Generate dummy performance
    midifile = '../midi/etude_op10_No3_deadpan.mid'
    outfile = '../bm_files/etude_op10_No3_dummybm.txt'
    compute_dummy_preds_from_midi(midifile, outfile)

    # Load dummy BM predictions
    score_dict = load_bm_preds(outfile)

    # Get unique onsets
    unique_onsets = np.array(list(score_dict.keys()))
    unique_onsets.sort()

    # initialize dummy controller
    controller = DummyController()

    # Start producing the MIDI messages
    prev_eq_onset = 0.5
    vel_min = 30
    vel_max = 110
    init_time = time.time()
    off_messages = []
    with mido.open_output(selected_port_name) as outport:
        for on in unique_onsets:

            (pitch, ioi, dur,
             vt, vd, lbpr,
             tim, lart, mel) = score_dict[on]

            bpr_a = 60.0 / controller.tempo
            vel_a = controller.velocity

            c_time = time.time() - init_time

            # Simulate controller input
            if c_time > 10 and c_time < 15:
                controller.tempo = 180
                controller.velocity = 90
            elif c_time > 15:
                controller.tempo = 210
                controller.velocity = 50

            eq_onset = prev_eq_onset + (2 ** lbpr) * bpr_a * ioi
            prev_eq_onset = eq_onset

            perf_onset = eq_onset - tim

            perf_onset_idx = np.argsort(perf_onset)

            perf_onset = perf_onset[perf_onset_idx]

            perf_duration = ((2 ** lart) * bpr_a * dur)[perf_onset_idx]

            perf_vel = np.clip(np.round((vt * vel_a - vd * 64)), vel_min,
                               vel_max).astype(np.int)[perf_onset_idx]
            pitch = pitch[perf_onset_idx]

            on_messages = []

            for p, o, d, v in zip(pitch, perf_onset, perf_duration, perf_vel):

                on_msg = Message('note_on', velocity=v, note=p, time=o)
                off_msg = Message('note_off', velocity=v, note=p, time=o+d)
                on_messages.append(on_msg)
                off_messages.append(off_msg)

            off_messages.sort(key=lambda x: x.time)

            while len(on_messages) > 0:

                current_time = time.time() - init_time
                if current_time >= on_messages[0].time:
                    print(on_messages[0])
                    outport.send(on_messages[0])
                    del on_messages[0]

                if len(off_messages) > 0:
                    current_time = time.time() - init_time
                    if current_time >= off_messages[0].time:
                        outport.send(off_messages[0])
                        print(off_messages[0])
                        del off_messages[0]

        # Send remaining note off messages
        while len(off_messages) > 0:
            current_time = time.time() - init_time
            if current_time >= off_messages[0].time:
                outport.send(off_messages[0])
                print(off_messages[0])
                del off_messages[0]


if __name__ == '__main__':

    test_dummy_performance_generation()
