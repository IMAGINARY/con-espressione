# LeapControl

Mimicking real performances from sheet music with the computer constitutes a
challenging research problem. There exist a few systems which are either
rule-based---following common performance rules in classical music---or
driven by learnd performance models.
LeapControl wraps such a data-driven performance model
(called the Non-linear Basis Mixer) in an interactive user interface.
Through the LeapMotion sensor, the user is able to control
the global dynamics and tempo deviations for classical piano pieces
with hand movements.
In the background, the computer model adds subtle modifications to the
performance such as slight temporal differences in the note onsets
when playing chords.
As output, LeapControl creates Midi events which are currently played back
through a synthesizer (FluidSynth) but these events could also be used
to control a player-piano as produced by Bösendorfer or Yamaha.

Note: If no LeapMotion sensor is available, tempo and dynamics can be controlled
through mouse movements.

## Setup

Download and install LeapMotion SDK from the Developer website: xxxx

We recommend Anaconda to fullfil the Python requirements.
All needed packages can be installed through:

```
    conda env create -f environment.yml
```

### Linux Specific

LeapMotion SDK installation guide: https://support.leapmotion.com/hc/en-us/articles/223782608-Linux-Installation

```
    sudo apt install libasound2-dev libjack-dev libusb-1.0-0-dev libudev-dev fluidsynth
```

If you want to use the knob to control the AI level, you need to add this
udev rule: https://github.com/signal11/hidapi/blob/master/udev/99-hid.rules

Please set the `idVendor` to `077d` `idProduct` to `0410` in lines 12 and 20.

### Mac Specific

```
    conda install -c conda-forge fluidsynth
```

## Run

```
    source activate leapcontrol
    python gui.py
```

By pressing `F1`, you can adapt LeapControl's configuration.

## Playback

LeapControl has two playback modes: Midi rendering and Basis Mixer.
With Midi rendering, you can load any piano Midi file with LeapControl and
control its tempo and dynamics.
However, the Basis Mixer requires a special file format which basically is a CSV
containing a list of note events (first three rows) plus a pre-computed
six-dimensional parameter vector which stores additional performance
information.

Furthermore, FluidSynth needs a soundfont for playback. This soundfont should
be located in the folder `sound_font` in the root directory. The soundfont
itself should be renamed to `default.sf2`.

## MIDI Interface

### Inputs

* Control Change, channel=0, control=20: LeapMotion X coordinate, [0, 127]
* Control Change, channel=0, control=21: LeapMotion Y coordinate, [0, 127]
* Control Change, channel=0, control=22: ML-Scaler, [0, 127]
* Control Change, channel=0, control=xx: Play, value=127
* Control Change, channel=0, control=xx: Stop, value=127

### Outputs

* Control Change, channel=1, control=110: Vis 1, [0, 127]
* Control Change, channel=1, control=111: Vis 2, [0, 127]
* Control Change, channel=1, control=112: Vis 3, [0, 127]
* Control Change, channel=1, control=113: Vis 4, [0, 127]
* Control Change, channel=1, control=114: Vis 5, [0, 127]

## Funding

This project has received funding from the European Research Council (ERC) under the European Union's Horizon 2020 research and innovation programme (grant agreement number 670035).

## References

Carlos E. Cancino-Chacón1, Maarten Grachten, Werner Goebl and Gerhard Widmer:
Computational Models of Expressive Music Performance: A Comprehensive and Critical Review. In Frontiers in Digital Humanities, 5:25. doi: 10.3389/fdigh.2018.00025
