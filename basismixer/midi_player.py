import asyncio
import time
import threading


class MidiPlayer:
    def __init__(self, midi_outport):
        self._midi_outport = midi_outport
        self._stop = False
        self._event_loop = asyncio.new_event_loop()
        self._stop = False
        self._thread = threading.Thread(
            name="MidiPlayer ({name})".format(name=midi_outport.name),
            target=lambda: self._run()
            )
        self._thread.start()

    def send(self, message, timestamp=time.time()):
        print(message)
        message_copy = message.copy()

        delay = time.time() - timestamp

        def schedule_message():
            self._event_loop.call_later(delay, lambda: self._midi_outport.send(message_copy))

        self._event_loop.call_soon_threadsafe(schedule_message)

    def _run(self):
        asyncio.set_event_loop(self._event_loop)
        self._event_loop.run_forever()

    def __del__(self):
        self._event_loop.stop()
