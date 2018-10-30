#!/usr/bin/env python3

"""
taken and adapted from https://github.com/bethebunny/powermate
Necessary steps before using the powermate:

$ sudo groupadd input
$ sudo usermod -a -G input "$USER"
$ echo 'KERNEL=="event*", NAME="input/%k", MODE="660", GROUP="input"' | sudo tee -a /etc/udev/rules.d/99-input

Afterwards a reboot is necessary
"""

from __future__ import print_function

import collections
try:
    import queue
except ImportError:
    import Queue as queue
import struct
import threading
import traceback


EV_MSC = 0x04
MSC_PULSELED = 0x01

EVENT_FORMAT = 'llHHi'
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

PUSH = 0x01
ROTATE = 0x02
MAX_BRIGHTNESS = 255
MAX_PULSE_SPEED = 255

# We don't want a huge backlog of events, otherwise we get bad situations where
# the listener is processing really old events and takes a while to catch up to
# current ones. If a listener is slow the expected behavior is to drop events
# for that listener.
MAX_QUEUE_SIZE = 5


class EventNotImplemented(NotImplementedError):
    """Special exception type for non-implemented events."""


class Event(object):
    def __init__(self, tv_sec, tv_usec, type, code, value):
        self.tv_sec = tv_sec
        self.tv_usec = tv_usec
        self.type = type
        self.code = code
        self.value = value

    def raw(self):
        return struct.pack(EVENT_FORMAT, self.tv_sec, self.tv_usec,
                           self.type, self.code, self.value)

    @classmethod
    def fromraw(cls, data):
        tv_sec, tv_usec, type, code, value = struct.unpack(EVENT_FORMAT, data)
        return cls(tv_sec, tv_usec, type, code, value)

    def __repr__(self):
        return '{}({})'.format(
          self.__class__.__name__,
          ', '.join('{}={}'.format(k, getattr(self, k))
                    for k in self.__dict__ if not k.startswith('_'))
        )


class LedEvent(Event):
    def __init__(self, brightness=MAX_BRIGHTNESS, speed=0,
                 pulse_type=0, asleep=0, awake=0):
        self.brightness = brightness
        self.speed = speed
        self.pulse_type = pulse_type
        self.asleep = asleep
        self.awake = awake
        self.type = EV_MSC
        self.code = MSC_PULSELED
        self.tv_sec, self.tv_usec = 0, 0

    @property
    def value(self):
        return (
          self.brightness |
          (self.speed << 8) |
          (self.pulse_type << 17) |
          (self.asleep << 19) |
          (self.awake << 20)
        )

    @classmethod
    def pulse(cls):
        return cls(speed=MAX_PULSE_SPEED, pulse_type=2, asleep=1, awake=1)

    @classmethod
    def max(cls):
        return cls(brightness=MAX_BRIGHTNESS)

    @classmethod
    def off(cls):
        return cls(brightness=0)

    @classmethod
    def percent(cls, percent):
        return cls(brightness=int(percent * MAX_BRIGHTNESS))


class FileEventSource(object):
    """An event source which reads and writes to a file object."""
    def __init__(self, path, event_size):
        self.__event_size = event_size
        self.__event_in = open(path, 'rb')
        self.__event_out = open(path, 'wb')

    def __iter__(self):
        """Read events from the source sequentially."""
        data = b''
        while True:
            data += self.__event_in.read(EVENT_SIZE)
            if len(data) >= EVENT_SIZE:
                event = Event.fromraw(data[:EVENT_SIZE])
                data = data[EVENT_SIZE:]
                yield event

    def send(self, event):
        """Write an event to the source."""
        self.__event_out.write(event.raw())
        self.__event_out.flush()


class EventQueue(object):
    """A thread-safe event queue which registers any number of listeners
    for an event source.

    This will store a small number of items in order for a listener to read,
    and they are then available to iterate over. If more events than the
    specified maximum are in a listener's queue, it will stop enqueueing new
    events. If for instance a listener takes a long break and max_queue_size
    is K, it will read the next K events after the sleep started (the oldest
    K events not read) and then continue to read new events. Any intermediate
    events will be dropped for that listener.

    Listeners may be simply registered by iterating over the queue, or
    through the .iterate method for more configuration.
    """
    def __init__(self, source, max_queue_size=MAX_QUEUE_SIZE):
        self.source = source
        self.queues = collections.OrderedDict()
        self._lock = threading.Lock()
        self.max_queue_size = max_queue_size

    def __iter__(self):
        return self.iterate()

    def iterate(self, max_queue_size=None):
        """Register a listener on the queue, and retrieve an iterator for them."""
        q = queue.Queue(max_queue_size or self.max_queue_size)
        key = object()
        with self._lock:
            self.queues[key] = q

        def iter_queue():
            try:
                while True:
                    yield q.get()
            except GeneratorExit:
                with self._lock:
                    del self.queues[key]

        return iter_queue()

    def watch(self):
        """Watch the underlying event source for events and
           send them to each registered queue."""
        for event in self.source:
            with self._lock:
                active_queues = list(self.queues.values())
            for q in active_queues:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    pass

    def send(self, event):
        """Send an event to the underlying event source."""
        self.source.send(event)


class EventHandler(object):
    def handle_events(self, source):
        for event in source:
            try:
                return_event = self.handle_event(event)
            except EventNotImplemented:
                pass
            except Exception as e:
                traceback.print_exc()
            else:
                if return_event is not None:
                  source.send(return_event)

    def handle_event(self, event):
        raise EventNotImplemented


class PowerMateEventHandler(EventHandler):
    def __init__(self, long_threshold=1000):
        self.__rotated = False
        self.button = 0
        self.__button_time = 0
        self.__long_threshold = long_threshold

    def handle_event(self, event):
        if event.type == PUSH:
            time = event.tv_sec * 10 ** 3 + (event.tv_usec * 10 ** -3)
            self.button = event.value
            if event.value:  # button depressed
                self.__button_time = time
                self.__rotated = False
            else:
                # If we have rotated this push, don't execute a push
                if self.__rotated:
                    return
                if time - self.__button_time > self.__long_threshold:
                    return self.long_press()
                else:
                    return self.short_press()
        elif event.type == ROTATE:
            if self.button:
                self.__rotated = True
                return self.push_rotate(event.value)
            else:
                return self.rotate(event.value)

        raise EventNotImplemented('unknown')

    def short_press(self):
        raise EventNotImplemented('short_press')

    def long_press(self):
        # default to short press if long press is not defined
        return self.short_press()

    def rotate(self, rotation):
        raise EventNotImplemented('rotate')

    def push_rotate(self, rotation):
        raise EventNotImplemented('push_rotate')


class AsyncFileEventDispatcher(object):
    def __init__(self, path, event_size=EVENT_SIZE):
        self.__filesource = FileEventSource(path, event_size)
        self.__source = EventQueue(self.__filesource)
        self.__threads = []

    def add_listener(self, event_handler):
        thread = threading.Thread(target=event_handler.handle_events,
                                  args=(self.__source,))
        thread.daemon = True
        thread.start()
        self.__threads.append(thread)

    def send_event(self, event):
        self.__source.send(event)

    def run(self):
        self.__source.watch()


class PowerMateBase(AsyncFileEventDispatcher, PowerMateEventHandler):
    def __init__(self, path, long_threshold=1000):
        AsyncFileEventDispatcher.__init__(self, path)
        PowerMateEventHandler.__init__(self, long_threshold)
        self.add_listener(self)

