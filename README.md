# Con Espressione!

Mimicking real performances from sheet music with the computer constitutes a
challenging research problem. There exist a few systems which are either
rule-based – following common performance rules in classical music – or
driven by learned performance models.
This software provides a wrapper for such a data-driven performance model
(called the Non-linear Basis Mixer).

Through MIDI control change messages, the user is able to control
the global dynamics and tempo deviations for classical piano pieces
with hand movements.
In the background, the computer model adds subtle modifications to the
performance such as slight temporal differences in the note onsets
when playing chords.
As output, it creates MIDI events which can be played back via any software
based piano synthesizer or even via a player-piano as produced by Bösendorfer
or Yamaha.

## Installation

Download the precompiled binary for your platform from the release section, rename it to `con-espressione` and make it executable (`chmod +x con-espressione` on the command line).

If binaries are not available for your platform, see the [build instructions](Development) below.

## Usage 

Run the binary with the following command:
```
./con-espressione
```
or use
```
pipenv run start
```
when in [development mode](Development).

By default, the app does not generate any console output during normal operation, but additional logging can be enabled by adding (multiple) `-v` flags to the command line.

### MIDI Interface

The app is controlled via MIDI messages to its `con-espressione` MIDI input port and sends MIDI music and status messages to its `con-espressione` MIDI output port. See [MIDI Interface](#midi-interface) for details.

#### Inputs

* Control Change, channel=0, control=20: LeapMotion X coordinate, [0, 127]
* Control Change, channel=0, control=21: LeapMotion Y coordinate, [0, 127]
* Control Change, channel=0, control=22: ML-Scaler, [0, 127]
* Song Select, [0, 127]
* Control Change, channel=0, control=24: Play, value=127
* Control Change, channel=0, control=25: Stop, value=127

#### Music outputs

The generated notes are sent on output channel 0. This channel should be connected to a software synthesizer or a player piano.

#### Status outputs

* Control Change, channel=1, control=110: Vis 1, [0, 127]
* Control Change, channel=1, control=111: Vis 2, [0, 127]
* Control Change, channel=1, control=112: Vis 3, [0, 127]
* Control Change, channel=1, control=113: Vis 4, [0, 127]
* Control Change, channel=1, control=114: Vis 5, [0, 127]
* Control Change, channel=1, control=115: End of a song signal, value=127

### Basis Mixer files

The Basis Mixer requires a special file format which basically is a CSV
containing a list of note events (first three rows) plus a pre-computed
six-dimensional parameter vector which stores additional performance
information. See `src/con-espressione/basis_mixer` for the included compositions.

## Development

We use [Pipenv](https://pipenv.pypa.io/en/latest/) for managing dependencies and virtual environments and it must be installed before you proceed.

To install the runtime dependencies, run
```
pipenv sync 
```
To install development dependencies as well, run
```
pipenv sync --dev
```

To run the app in development mode, use
```
pipenv run start
```

To build the redistributable binaries for the app, run
```
pipenv run build-platform
```
where `platform` is one of `linux-x86_64`, `linux-aarch64`, `macos-x86_64`, or `macos-arm64`.

The build results will be placed in the `dist` directory.

## Frontends

This software serves as a backend and should be combined with a [frontend for user interaction](https://github.com/IMAGINARY/con-espressione-ui).

## Funding

This project has received funding from the European Research Council (ERC) under the European Union's Horizon 2020 research and innovation programme (grant agreement number 670035).

<img src="https://erc.europa.eu/sites/default/files/LOGO_ERC-FLAG_EU_.jpg" width="35%" height="35%">


## References

> Carlos E. Cancino-Chacón, Maarten Grachten, Werner Goebl and Gerhard Widmer:<br />
*Computational Models of Expressive Music Performance: A Comprehensive and Critical Review.*<br />In Frontiers in Digital Humanities, 5:25. doi: 10.3389/fdigh.2018.00025

## License

This project is licensed under the Apache v2.0 license. See the `LICENSE` file for the license text.
