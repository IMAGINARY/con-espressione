# import threading
from threading import Thread
import mido
import time
import numpy as np
import json


class MIDIController():

    def __init__(self, midi_port):

        # threading.Thread.__init__(self)
        self.midi_port = midi_port
        self.faders = np.arange(8)
        self.knobs = np.arange(16, 24)

    def run(self):

        with mido.open_input(self.midi_port) as inport:

            for msg in inport:

                if msg.type == 'control_change':
                    # print(msg)

                    if msg.control in self.faders:
                        print('fader', msg.control - self.faders.min(),
                              msg.value)
                    elif msg.control in self.knobs:
                        print('knob', msg.control - self.knobs.min(),
                              msg.value)
                time.sleep(1e-3)


class BMKnob(object):
    def __init__(self, min_value, max_value, name='', init_value=0.0):
        self.value = init_value
        self.name = name
        self.max_value = max_value
        self.min_value = min_value

    def update(self, value):

        self.value = np.clip(value * (self.max_value - self.min_value) +
                             self.min_value,
                             self.min_value, self.max_value)


class BMControllerThread(Thread):
    def __init__(self,
                 vt_mean,
                 vt_std,
                 vd_mean,
                 vd_std,
                 lbpr_mean,
                 lbpr_std,
                 tim_mean,
                 tim_std,
                 lart_mean,
                 lart_std,
                 vt_mean_ctrl=0,
                 vt_std_ctrl=16,
                 vd_mean_ctrl=1,
                 vd_std_ctrl=17,
                 lbpr_mean_ctrl=2,
                 lbpr_std_ctrl=18,
                 tim_mean_ctrl=3,
                 tim_std_ctrl=19,
                 lart_mean_ctrl=4,
                 lart_std_ctrl=20,
                 midi_port='nanoKONTROL2 SLIDER/KNOB'):
        Thread.__init__(self)

        self.vt_mean = vt_mean
        self.vt_std = vt_std
        self.vt_mean_ctrl = vt_mean_ctrl
        self.vt_std_ctrl = vt_std_ctrl

        self.vd_mean = vd_mean
        self.vd_std = vd_std
        self.vd_mean_ctrl = vd_mean_ctrl
        self.vd_std_ctrl = vd_std_ctrl

        self.lbpr_mean = lbpr_mean
        self.lbpr_std = lbpr_std
        self.lbpr_mean_ctrl = lbpr_mean_ctrl
        self.lbpr_std_ctrl = lbpr_std_ctrl

        self.tim_mean = tim_mean
        self.tim_std = tim_std
        self.tim_mean_ctrl = tim_mean_ctrl
        self.tim_std_ctrl = tim_std_ctrl

        self.lart_mean = lart_mean
        self.lart_std = lart_std
        self.lart_mean_ctrl = lart_mean_ctrl
        self.lart_std_ctrl = lart_std_ctrl

        self.knobs = [self.vt_mean,
                      self.vt_std,
                      self.vd_mean,
                      self.vd_std,
                      self.lbpr_mean,
                      self.lbpr_std,
                      self.tim_mean,
                      self.tim_std,
                      self.lart_mean,
                      self.lart_std]

        self.ctrls = [self.vt_mean_ctrl,
                      self.vt_std_ctrl,
                      self.vd_mean_ctrl,
                      self.vd_std_ctrl,
                      self.lbpr_mean_ctrl,
                      self.lbpr_std_ctrl,
                      self.tim_mean_ctrl,
                      self.tim_std_ctrl,
                      self.lart_mean_ctrl,
                      self.lart_std_ctrl]

        self.midi_port = midi_port

    def run(self):
        with mido.open_input(self.midi_port) as inport:
            for msg in inport:
                if msg.type == 'control_change':
                    if msg.control in self.ctrls:
                        k_idx = self.ctrls.index(msg.control)
                        self.knobs[k_idx].update(float(msg.value) / 127.0)
                time.sleep(1e-5)

    def dump_config(self, outfile=None):
        config = dict(
            vel_dev=dict(
                mean=self.vd_mean.value,
                std=self.vd_std.value),
            log_bpr=dict(
                mean=self.lbpr_mean.value,
                std=self.lbpr_std.value),
            timing=dict(
                mean=self.tim_mean.value,
                std=self.tim_std.value),
            log_art=dict(
                mean=self.lart_mean.value,
                std=self.lart_std.value))

        if outfile is not None:
            with open(outfile, 'w') as f:
                json.dump(config, f, indent=4)

        return config

            
                


if __name__ == '__main__':

    # input_ports = mido.get_input_names()

    # print(input_ports)

    # midi_port_nr = int(input())
    # midi_port = input_ports[midi_port_nr]

    # mc = MIDIController(midi_port)

    # mc.run()

    # faders = np.arange(8)
    # knobs = np.arange(16, 24)

    vt_mean = BMKnob(30, 90)
    vt_std = BMKnob(1, 10)
    vd_mean = BMKnob(-30, 30)
    vd_std = BMKnob(1, 5)
    lbpr_mean = BMKnob(-2, 2)
    lbpr_std = BMKnob(0.1, 2)
    tim_mean = BMKnob(-0.1, 0.1)
    tim_std = BMKnob(0.1, 1.5)
    lart_mean = BMKnob(-3, 3)
    lart_std = BMKnob(0.1, 3)

    bc = BMControllerThread(vt_mean=vt_mean,
                            vt_std=vt_std,
                            vd_mean=vd_mean,
                            vd_std=vd_std,
                            lbpr_mean=lbpr_mean,
                            lbpr_std=lbpr_std,
                            tim_mean=tim_mean,
                            tim_std=tim_std,
                            lart_mean=lart_mean,
                            lart_std=lart_std)
    bc.daemon = True
    bc.start()
