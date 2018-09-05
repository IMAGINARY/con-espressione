"""
    Threading class for MIDI playback.
"""
import threading
import time
import mido


class MidiThread(threading.Thread):
    def __init__(self, midi_path, midi_port):
        threading.Thread.__init__(self)
        self.midi = midi_path
        self.midi_port = midi_port
        self.vel = None
        self.tempo = 1

    def set_velocity(self, vel):
        self.vel = vel

    def set_tempo(self, tempo):
        self.tempo = tempo

    def run(self):
        with mido.open_output(self.midi_port) as outport:
            for msg in mido.MidiFile(self.midi):
                play_msg = msg
                if msg.type == 'note_on':
                    if msg.velocity != 0 and self.vel is not None:
                        play_msg = msg.copy(velocity=self.vel)

                time.sleep(play_msg.time*self.tempo)

                outport.send(play_msg)
