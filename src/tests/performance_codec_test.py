"""
    Tests for performance generation using the precomputed
    inputs of the Basis Mixer.
"""
import mido
import numpy as np
import time

from mido import Message

from basismixer.performance_codec import (load_bm_preds,
                                          compute_dummy_preds_from_midi,
                                          get_unique_onsets)


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
                               vel_max).astype(int)[perf_onset_idx]
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


def test_remove_trend():
    import matplotlib.pyplot as plt
    from basismixer.bm_utils import remove_trend
    fn = '../bm_files/chopin_op10_No3_bm_magaloff.txt'
    bm_data = np.loadtxt(fn)
    onsets = bm_data[:, 1]
    unique_onsets, unique_onset_idxs = get_unique_onsets(onsets)

    vel_trend = np.array([bm_data[ix, 3].mean() for ix in unique_onset_idxs])
    vt_trendless, vt_smoothed = remove_trend(vel_trend, unique_onsets, 'savgol',
                                             return_smoothed_param=True)
    x = unique_onsets
    y = vel_trend
    yhat = vt_smoothed

    plt.plot(x, y / vel_trend.mean())
    plt.plot(x, yhat / vel_trend.mean(), color='red')
    plt.plot(x, vt_trendless / vel_trend.mean(), color='black')
    plt.show()


def test_pedal():
    import json
    from basismixer.performance_codec import PerformanceCodec
    fn = '../bm_files/beethoven_op027_no2_mv1_bm_of_wm.txt'
    config_fn = fn.replace('.txt', '.json')
    pedal_fn = fn.replace('.txt', '.pedal')

    config = json.load(open(config_fn))

    score = load_bm_preds(filename=fn, post_process_config=config,
                          pedal_fn=pedal_fn)

    pc = PerformanceCodec(tempo_ave=60. / config['tempo_ave'],
                          velocity_ave=config['velocity_ave'],
                          vel_min=config['vel_min'],
                          vel_max=config['vel_max'])

    note_info, pedal = pc.decode_offline(score)

    ports = mido.get_output_names()
    port = mido.open_output(ports[0])

    note_info = note_info[note_info[:, 1].argsort()]
    pedal = pedal[pedal[:, 0].argsort()]

    midi_messages = []

    for n, on, off, v in note_info:
        on_msg = Message('note_on', note=int(n), velocity=int(v), time=on)
        off_msg = Message('note_off', note=int(n), time=off)

        midi_messages.append(on_msg)
        midi_messages.append(off_msg)

    for on, p in pedal:

        midi_messages.append(
            Message('control_change', control=64, value=int(p) * 127, time=on))

    midi_messages.sort(key=lambda x: x.time)

    init_time = time.time()
    while len(midi_messages) > 0:

        current_time = time.time() - init_time

        if current_time >= midi_messages[0].time:
            port.send(midi_messages[0])
            del midi_messages[0]

        time.sleep(1e-4)

    port.close()


if __name__ == '__main__':

    # test_dummy_performance_generation()
    import json
    from basismixer.performance_codec import PerformanceCodec
    fn = '../bm_files/beethoven_op027_no2_mv1_bm_of_wm.txt'
    config_fn = fn.replace('.txt', '.json')
    pedal_fn = fn.replace('.txt', '.pedal')

    config = json.load(open(config_fn))

    score_dict = load_bm_preds(filename=fn, post_process_config=config,
                               pedal_fn=pedal_fn)

    pc = PerformanceCodec(tempo_ave=config['tempo_ave'],
                          velocity_ave=config['velocity_ave'],
                          vel_min=config['vel_min'],
                          vel_max=config['vel_max'])

    unique_onsets = np.array(list(score_dict.keys()))
    unique_onsets.sort()

    bpr_a = pc.tempo_ave
    vel_a = pc.velocity_ave

    on_messages = []
    off_messages = []
    ped_messages = []
    currently_sounding_pitches = []
    for on in unique_onsets:
        # Get score and performance info
        (pitch, ioi, dur,
         vt, vd, lbpr,
         tim, lart, mel, ped) = score_dict[on]

        _on_messages, _off_messages, _ped_messages = pc.decode_online(
            pitch=pitch, ioi=ioi, dur=dur, vt=vt,
            vd=vd, lbpr=lbpr, tim=tim, lart=lart,
            mel=mel, bpr_a=bpr_a, vel_a=vel_a, ped=ped)

        on_messages += _on_messages
        off_messages += _off_messages
        ped_messages += _ped_messages

    ports = mido.get_output_names()
    port = mido.open_output(ports[0])

    midi_messages = on_messages + off_messages + ped_messages

    midi_messages.sort(key=lambda x: x.time)

    init_time = time.time()
    while len(midi_messages) > 0:

        current_time = time.time() - init_time

        if current_time >= midi_messages[0].time:

            if midi_messages[0].type == 'note_on':
                if midi_messages[0].note in currently_sounding_pitches:
                    csp_ix = currently_sounding_pitches.index(
                        midi_messages[0].note)
                    del currently_sounding_pitches[csp_ix]
                    for noi, msg in enumerate(midi_messages):
                        if msg.type == 'note_off':
                            if msg.note == midi_messages[0].note:
                                port.send(msg)
                                print('deleted', msg)
                                del midi_messages[noi]

                                break
                currently_sounding_pitches.append(midi_messages[0].note)

            port.send(midi_messages[0])
            if midi_messages[0].type == 'note_off':
                if midi_messages[0].note in currently_sounding_pitches:
                    csp_ix = currently_sounding_pitches.index(
                        midi_messages[0].note)
                    del currently_sounding_pitches[csp_ix]
            del midi_messages[0]

        time.sleep(1e-4)

    port.close()
