"""
    Run the Demo
"""
import argparse
import asyncio
import logging
import mido
import platform

from basismixer.midi_player import MidiPlayer
from leap_control import LeapControl


async def main():
    CONFIG = {'playmode': 'BM',
              'driver': 'alsa' if platform.system() == 'Linux' else 'coreaudio',
              'control': 'Mouse',
              'bm_file': 'bm_files/beethoven_op027_no2_mv1_bm_z.txt',
              'bm_config': 'bm_files/beethoven_op027_no2_mv1_bm_z.json'}

    SONG_LIST = ['bm_files/beethoven_op027_no2_mv1_bm_z.txt',
                 'bm_files/chopin_op10_No3_v422.txt',
                 'bm_files/mozart_kv545_mv2.txt',
                 'bm_files/beethoven_fuer_elise_complete.txt']

    midi_outport = mido.open_output('con-espressione', virtual=True)
    midi_player = MidiPlayer(midi_outport)
    midi_inport = mido.open_input('con-espressione', virtual=True)

    # instantiate LeapControl
    lc = LeapControl(CONFIG, SONG_LIST, midi_player)

    try:
        # listen to input MIDI port for messages
        for msg in lc.midi_inport:
            await lc.parse_midi_msg(msg)
    except AttributeError as e:
        print('Received unrecognized MIDI message.')
        print(e)
    except KeyboardInterrupt:
        print('Received keyboard interrupt. Shutting down...')
    finally:
        # clean-up
        await lc.stop()
        if lc.playback_thread is not None:
            await lc.playback_thread.join()
        midi_outport.close()
        midi_inport.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backend for BM-Application.')
    parser.add_argument('--verbose', help='Print Debug logs.', action='store_true')
    args = parser.parse_args()

    # set logging level
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # start backend
    asyncio.run(main())
