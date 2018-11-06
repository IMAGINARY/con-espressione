"""
Helper methods to load the precomputed performance and score information
from the Basis Mixer.

TODO
----
* Add melody lead
"""
import numpy as np
from mido import Message


def standardize(array):
    if not np.isclose(array.std(), 0):

        return (array - array.mean()) / (array.std())
    else:
        return (array - array.mean())


def minmax_normalize(array):
    return (array - array.min()) / (array.max() - array.min())


class PerformanceCodec(object):
    """Performance Codec

    This class provides methods for decoding a performance to MIDI file.
    """

    def __init__(self, tempo_ave=55,
                 velocity_ave=50,
                 vel_min=30, vel_max=110,
                 init_eq_onset=0.0):
        self.vel_min = vel_min
        self.vel_max = vel_max
        self.tempo_ave = 60.0 / float(tempo_ave)
        self.velocity_ave = velocity_ave
        self.prev_eq_onset = init_eq_onset
        self.midi_messages = []
        self._init_eq_onset = init_eq_onset
        self._bp = self.tempo_ave

    def _decode_step(self, ioi, dur, vt, vd, lbpr,
                     tim, lart, mel, bpr_a, vel_a):
        """Compute performed onset, duration and MIDI velocity
        for the current onset time.
        Parameters
        ----------
        ioi: float
            Score IOI (in beats)
        dur : array
            Notated duration of the notes in beats
        vt : float
            MIDI velocity trend ratio corresponding to the current
            score position.
        vd : array
            MIDI velocity deviations of the notes of the currrent
            score position
        lbpr : float
            Log beat period ratio corresponding to the current
            score position
        tim : array
            Timing deviations of the notes of the current score position.
        lart : array
            Log articulation ratio of the notes of the current score position.
        mel : array
            Melody lead (TODO: add melody lead)
        bpr_a : float
            Average beat period corresponding to the current score position.
        vel_a : float
            Average MIDI velocity corresponding to the current score position.

        Returns
        -------
        perf_onset : array
            Performed onset time in seconds of the notes in the current score
            position.
        perf_duration : array
            Performed duration in seconds of the notes in the current score
            position.
        perf_vel : array
            Performed MIDI velocity of the notes in the current score position
        """
        # Compute equivalent onset
        bp = (2 ** lbpr) * bpr_a

        eq_onset = self.prev_eq_onset + self._bp * ioi

        self._bp = bp
        # Compute onset for all notes in the current score position
        perf_onset = eq_onset - tim

        # Update previous equivalent onset
        self.prev_eq_onset = eq_onset

        # Compute performed duration for each note
        perf_duration = ((2 ** lart) * bp * dur)

        # Compute performed MIDI velocity for each note
        perf_vel = np.clip(np.round(vt * vel_a - vd),
                           a_min=self.vel_min,
                           a_max=self.vel_max).astype(np.int)
        return perf_onset, perf_duration, perf_vel

    def decode_online(self, pitch, ioi, dur, vt, vd, lbpr,
                      tim, lart, mel, bpr_a, vel_a):
        """Decode the expressive performance of the notes at the same
        score position and output the corresponding MIDI messages.

        This method is designed to be used as part of the `BMThread`

        Parameters
        ----------
        ioi: float
            Score IOI (in beats)
        dur : array
            Notated duration of the notes in beats
        vt : float
            MIDI velocity trend ratio corresponding to the current
            score position.
        vd : array
            MIDI velocity deviations of the notes of the currrent
            score position
        lbpr : float
            Log beat period ratio corresponding to the current
            score position
        tim : array
            Timing deviations of the notes of the current score position.
        lart : array
            Log articulation ratio of the notes of the current score position.
        mel: array
            Melody lead
        bpr_a : float
            Average beat period corresponding to the current score position.
        vel_a : float
            Average MIDI velocity corresponding to the current score position.

        Returns
        -------
        on_messages : list
            List of MIDI messages (as `Message` instances) corresponding to the
            note on messages
        off_messages : list
            List of MIDI messages (as `Message` instances) corresponding to the
            note off messages
        """

        # Get perfomed onsets and durations (in seconds) and MIDI velocities
        (perf_onset, perf_duration, perf_vel) = self._decode_step(ioi=ioi,
                                                                  dur=dur,
                                                                  vt=vt,
                                                                  vd=vd,
                                                                  lbpr=lbpr,
                                                                  tim=tim,
                                                                  lart=lart,
                                                                  mel=mel,
                                                                  bpr_a=bpr_a,
                                                                  vel_a=vel_a)
        # Indices to sort the notes according to their onset times
        osix = np.argsort(perf_onset)

        on_messages = []
        off_messages = []

        for p, o, d, v in zip(pitch[osix], perf_onset[osix],
                              perf_duration[osix], perf_vel[osix]):

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

        return on_messages, off_messages

    def decode_offline(self, score_dict, return_s_onsets=False):

        # Get unique score positions (and sort them)
        unique_onsets = np.array(list(score_dict.keys()))
        unique_onsets.sort()

        # Iterate over unique onsets
        pitches = []
        onsets = []
        durations = []
        velocities = []
        s_onsets = []
        for on in unique_onsets:
            (pitch, ioi, dur,
             vt, vd, lbpr,
             tim, lart, mel) = score_dict[on]

            (perf_onset, perf_duration, perf_vel) = self._decode_step(
                ioi=ioi,
                dur=dur,
                vt=vt,
                vd=vd,
                lbpr=lbpr,
                tim=tim,
                lart=lart,
                mel=mel,
                bpr_a=self.tempo_ave,
                vel_a=self.velocity_ave)

            pitches.append(pitch)
            onsets.append(perf_onset)
            durations.append(perf_duration)
            velocities.append(perf_vel)
            s_onsets.append(np.ones_like(perf_onset) * on)

        pitches = np.hstack(pitches)
        onsets = np.hstack(onsets)
        # performance starts at 0
        onsets -= onsets.min()
        durations = np.hstack(durations)
        velocities = np.hstack(velocities)
        s_onsets = np.hstack(s_onsets)

        note_info = np.column_stack(
            (pitches, onsets, onsets + durations, velocities))
        self.reset()
        if return_s_onsets:
            return note_info, s_onsets
        else:
            return note_info

    def reset(self):
        self.prev_eq_onset = self._init_eq_onset
        self._bp = self.tempo_ave


def load_bm_preds(filename, deadpan=False, post_process_config={}):
    """Loads precomputed predictions of the Basis Mixer.

    Parameters
    ----------
    filename : str
        File with the precomputed predictions of the Basis Mixer

    Returns
    -------
    score_dict : dict
        Dictionary containing score and performance information.
        The keys of the dictionary are the unique score positions.
        For each score position, there is a tuple containing:
        (0:Pitches, 1:score ioi, 2:durations, 3:vel_trend
         4:vel_dev, 5:log_bpr, 6:timing, 7:log_art,
         8:melody)
    """
    # Load predictions file
    bm_data = np.loadtxt(filename)
    # Score information
    pitches = bm_data[:, 0].astype(np.int)
    onsets = bm_data[:, 1]
    durations = bm_data[:, 2]
    melody = bm_data[:, 8]

    # Onsets start at 0
    onsets -= onsets.min()

    if not deadpan:
        # Performance information (expressive parameters)

        # Minmax velocity trend
        vel_trend = minmax_normalize(bm_data[:, 3])

        if 'vel_trend' in post_process_config:
            exag_exp = post_process_config['vel_trend'].get('exag_exp', 1.0)
            vel_trend = vel_trend ** exag_exp

        vel_trend /= vel_trend.mean()

        # Standardize vel_dev
        vel_dev = standardize(bm_data[:, 4])
        if 'vel_dev' in post_process_config:
            # Rescale and recenter parameters
            vd_std = post_process_config['vel_dev'].get('std', 1.0)
            vd_mean = post_process_config['vel_dev'].get('mean', 0.0)
            vel_dev = (vel_dev * vd_std) + vd_mean

        # Standardize log_bpr
        log_bpr = standardize(bm_data[:, 5])
        if 'log_bpr' in post_process_config:
            # Rescale and recenter parameters
            lb_std = post_process_config['log_bpr'].get('std', 1.0)
            lb_mean = post_process_config['log_bpr'].get('mean', 0.0)
            log_bpr = (log_bpr * lb_std) + lb_mean

        # Standardize timing
        timing = standardize(bm_data[:, 6])
        if 'timing' in post_process_config:
            # Rescale and recenter parameters
            ti_std = post_process_config['timing'].get('std', 1.0)
            ti_mean = post_process_config['timing'].get('mean', 0.0)
            timing = (timing * ti_std) + ti_mean

        # Standardize log articulation
        log_art = standardize(bm_data[:, 7])
        if 'log_art' in post_process_config:
            # Rescale and recenter parameters
            vd_std = post_process_config['log_art'].get('std', 1.0)
            vd_mean = post_process_config['log_art'].get('mean', 0.0)
            log_art = (log_art * vd_std) + vd_mean

    else:
        # Expressive parameters corresponding to a deadpan performance
        n_notes = len(pitches)
        vel_trend = np.ones(n_notes)
        vel_dev = np.zeros(n_notes)
        log_bpr = np.zeros(n_notes)
        timing = np.zeros(n_notes)
        log_art = np.zeros(n_notes)

    return _build_score_dict(pitches, onsets, durations, melody,
                             vel_trend, vel_dev, log_bpr,
                             timing, log_art)


def _build_score_dict(pitches, onsets, durations, melody,
                      vel_trend, vel_dev, log_bpr,
                      timing, log_art):
    """Helper method to build a dictionary with score and performance information
       for each score position.

    Parameters
    ----------
    pitches : np.array
        Array containing the MIDI pitch of each note in the score.
    onsets : np.array
        Array contaning the onset (in beats) of each note in the score.
    durations : np.array
        Array containing the duration (in beats) of each note in the score.
    melody : np.array
        Array of booleans indicating whether a note in the score is part of the
        melody.
    vel_trend : np.array
        Onset-wise MIDI velocity trend for each note (notes with the same score
        positions have the same MIDI velocity trend value).
    vel_dev : np.array
        Deviations from the trend in MIDI velocity for each note.
    log_bpr : np.array
        Base-2 logarithm of the beat period ratio (BPR) for each score position
        (notes with the same score position have the same log BPR value).
    timing : np.array
        Timing deviations from the equivalent performed onset for each note.
    log_art : np.array
        Base-2 logarithm of the articulation ratio for each note in the score.

    Returns
    -------
    score_dict : dict
        Dictionary containing score and performance information.
        The keys of the dictionary are the unique score positions.
        For each score position, there is a tuple containing:
        (0:Pitches, 1:ioi, 2:durations, 3:vel_trend
         4:vel_dev, 5:log_bpr, 6:timing, 7:log_art,
         8:melody)
    """
    # Get unique score positions
    unique_onsets = np.unique(onsets)
    unique_onsets.sort()
    # List of indices corresponding to each of the unique score positions
    unique_onset_idxs = [np.where(onsets == u)[0] for u in unique_onsets]

    # Compute IOIs
    iois = np.r_[0, np.diff(unique_onsets)]
    # Initialize score dict
    score_dict = dict()
    for on, ioi, ix in zip(unique_onsets, iois, unique_onset_idxs):
        # 0:Pitches, 1:ioi, 2:durations, 3:vel_trend
        # 4:vel_dev, 5:log_bpr, 6:timing, 7:log_art
        # 8:melody
        score_dict[on] = (pitches[ix],
                          ioi,
                          durations[ix],
                          np.mean(vel_trend[ix]),
                          vel_dev[ix],
                          np.mean(log_bpr[ix]),
                          timing[ix],
                          log_art[ix],
                          melody[ix])
    return score_dict


def compute_dummy_preds_from_midi(filename, outfile, deadpan=False):
    """Generate a dummy performance parameters given a score in MIDI file.
       This method is for testing purposes.

    Parameters
    ----------
    filename : str
        Score in MIDI file format.
    outfile : str
        File for saving the dummy predictions with the format required by
        `load_bm_preds`.
    deadpan : bool (default is False)
        If `True`, computes the expressive parameters corresponding to a
        deadpan performance. Otherwise, the expressive parameters are
        randomly generated.
    """
    # TODO: load midi using only mido
    import madmom.utils.midi as midi

    # Load MIDI file
    mf = midi.MIDIFile().from_file(filename).notes(unit='b')
    # Score information
    n_notes = len(mf)
    pitches = mf[:, 1]
    onsets = mf[:, 0]
    durations = mf[:, 2]
    melody = np.zeros(n_notes)

    # Onsets start at 0
    onsets -= onsets.min()

    if deadpan:
        # Expressive parameters corresponding to a deadpan performance
        vel_trend = np.ones(n_notes)
        vel_dev = np.zeros(n_notes)
        log_bpr = np.zeros(n_notes)
        timing = np.zeros(n_notes)
        log_art = np.zeros(n_notes)

    else:
        # Random performance information
        vel_trend = np.clip(1 - 0.05 * np.random.randn(n_notes), 0, 2)
        vel_dev = 0.1 * np.random.rand(n_notes)
        log_bpr = 0.1 * np.random.randn(n_notes)
        timing = 0.05 * np.random.randn(n_notes)
        log_art = 0.3 * np.random.randn(n_notes)

    # save to outfile
    bm_data = np.column_stack((pitches, onsets, durations,
                               vel_trend, vel_dev, log_bpr,
                               timing, log_art, melody))
    np.savetxt(outfile, bm_data)


def get_vis_scaling_factors(score_dict, max_scaler):

    vel_trend = []
    vel_dev = []
    log_bpr = []
    timing = []
    log_art = []
    for on in score_dict:
        (pitch, ioi, dur,
         vt, vd, lbpr,
         tim, lart, mel) = score_dict[on]

        vel_trend.append(vt)
        vel_dev.append(vd)
        log_bpr.append(lbpr)
        timing.append(tim)
        log_art.append(lart)

    vel_trend = np.array(vel_trend)
    vel_trend /= vel_trend.mean()

    vel_devc = np.hstack(vel_dev)
    log_bpr = np.array(log_bpr)
    timingc = np.hstack(timing)
    log_artc = np.hstack(log_art)

    vt_max = vel_trend.max() ** max_scaler
    vt_min = vel_trend.min() ** max_scaler

    vd_max = max_scaler * vel_devc.max()
    vd_min = max_scaler * vel_devc.min()

    lbpr_max = max_scaler * log_bpr.max()
    lbpr_min = max_scaler * log_bpr.min()

    tim_max = max_scaler * timingc.max()
    tim_min = max_scaler * timingc.min()

    lart_max = max_scaler * log_artc.max()
    lart_min = max_scaler * log_artc.min()

    return (vt_max, vt_min, vd_max, vd_min, lbpr_max, lbpr_min,
            tim_max, tim_min, lart_max, lart_min)


def compute_vis_scaling(vt, vd, lbpr, tim, lart, vis_scaling_factors):
    (vt_max, vt_min, vd_max, vd_min, lbpr_max, lbpr_min,
     tim_max, tim_min, lart_max, lart_min) = vis_scaling_factors

    vts = (vt - vt_min) / (vt_max - vt_min)
    vds = np.mean((vd - vd_min) / (vd_max - vd_min))
    lbprs = (lbpr - lbpr_min) / (lbpr_max - lbpr_min)
    tims = np.mean((tim - tim_min) / (tim_max - tim_min))
    larts = np.mean((lart - lart_min) / (lart_max - lart_min))

    return vts, vds, lbprs, tims, larts
