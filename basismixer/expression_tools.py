import numpy as np
# import matplotlib.pyplot as plt

# from performance_codec import load_bm_preds

# import json


def melody_lead(pitch, velocity, lead=0.01):
    """
    Compute melody lead
    """
    return (np.exp((pitch - 127.) / 127.) *
            np.exp(-(velocity - 127) / 127.) * lead)


def melody_lead_dyn(mel, velocity, vel_a, lead=0.1):
    # This is a Hack!
    l = (1 + lead)
    # return velocity * (1 + lead)
    if not np.all(~mel.astype(bool) == 0):
        return np.maximum(velocity[~mel.astype(bool)].argmax() * l,
                          vel_a * l)
    else:
        return vel_a * l
