# Con Espressione

Mimicking real performances from sheet music with the computer constitutes a
challenging research problem. There exist a few systems which are either
rule-based---following common performance rules in classical music---or
driven by learned performance models.
This software provides a wrapper for such a data-driven performance model
(called the Non-linear Basis Mixer).

Through MIDI control change messages messages, the user is able to control
the global dynamics and tempo deviations for classical piano pieces
with hand movements.
In the background, the computer model adds subtle modifications to the
performance such as slight temporal differences in the note onsets
when playing chords.
As output, it creates MIDI events which can be played back via any software
based piano synthesizer or even via a player-piano as produced by Bösendorfer
or Yamaha.

## Setup

We recommend Anaconda to fullfill the Python requirements.
All needed packages can be installed through:

```
    git clone ###REPO-URL###
    git submodule init
    git submodule update
    conda env create -f environment.yml
```

### Ubuntu Linux Specific

The following dependencies must be installed before creating the conda
environment:

```
    sudo apt install pkg-config libjack-dev
```

## Run

```
    source activate con_espressione
    python con_espressione.py
```

## Playback

Expressiveness has two playback modes: MIDI rendering and Basis Mixer.
With MIDI rendering, you can load any piano MIDI file with Expressiveness and
control its tempo and dynamics.
However, the Basis Mixer requires a special file format which basically is a CSV
containing a list of note events (first three rows) plus a pre-computed
six-dimensional parameter vector which stores additional performance
information.

## MIDI Interface

The MIDI device name to connect to is `con-espressione`.

### Inputs

* Control Change, channel=0, control=20: LeapMotion X coordinate, [0, 127]
* Control Change, channel=0, control=21: LeapMotion Y coordinate, [0, 127]
* Control Change, channel=0, control=22: ML-Scaler, [0, 127]
* Song Select, [0, 127]
* Control Change, channel=0, control=24: Play, value=127
* Control Change, channel=0, control=25: Stop, value=127

### Outputs

* Control Change, channel=1, control=110: Vis 1, [0, 127]
* Control Change, channel=1, control=111: Vis 2, [0, 127]
* Control Change, channel=1, control=112: Vis 3, [0, 127]
* Control Change, channel=1, control=113: Vis 4, [0, 127]
* Control Change, channel=1, control=114: Vis 5, [0, 127]
* Control Change, channel=1, control=115: End of a song signal, value=127

## Frontends

This software serves as a backend and should be combined with a frontend for user interaction (https://github.com/IMAGINARY/expressiveness-ui)
which is embedded in this repository as a submodule in the folder `web-ui`.

## Funding

This project has received funding from the European Research Council (ERC) under the European Union's Horizon 2020 research and innovation programme (grant agreement number 670035).

<img src="https://erc.europa.eu/sites/default/files/LOGO_ERC-FLAG_EU_.jpg" width="35%" height="35%">


## References

> Carlos E. Cancino-Chacón, Maarten Grachten, Werner Goebl and Gerhard Widmer:<br />
*Computational Models of Expressive Music Performance: A Comprehensive and Critical Review.*<br />In Frontiers in Digital Humanities, 5:25. doi: 10.3389/fdigh.2018.00025

## License

This project is licensed under the Apache v2.0 license. See the `LICENSE` file for the license text.
