"""
Helper methods to load the precomputed performance and score information
from the Basis Mixer.

TODO
----
* Move all decoding methods here (from ?
* Use only mido for generating dummy bm files from midi (remove dependencies
from madmom)
"""
import numpy as np


def load_bm_preds(filename):
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

    # Performance information (expressive parameters)
    vel_trend = bm_data[:, 3]
    vel_dev = bm_data[:, 4]
    log_bpr = bm_data[:, 5]
    timing = bm_data[:, 6]
    log_art = bm_data[:, 7]

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
