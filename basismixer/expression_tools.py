import numpy as np


def melody_lead(pitch, velocity, lead=0.01):
    """
    Compute melody lead
    """
    return (np.exp((pitch - 127.) / 127.) *
            np.exp(-(velocity - 127) / 127.) * lead)


def melody_lead_dyn(mel, velocity, vel_a, lead=0.2):
    # This is a Hack!
    l = (1 + lead)
    # return velocity * (1 + lead)
    if not np.all(~mel.astype(bool) == 0):
        return np.maximum(velocity[~mel.astype(bool)].argmax() * l,
                          vel_a * l)
    else:
        return vel_a * l


def scale_parameters(vt, vd, lbpr, tim, lart, pitch,
                     mel, ped, vel_a, bpr_a, controller_p=1.0,
                     remove_trend_vt=True):
    # Do not use melody lead in deadpan version
    mel = mel * (controller_p > 0)
    # add timing melody lead
    tim_ml = melody_lead(pitch, vel_a) * mel
    tim += tim_ml

    # add dynamics melody lead
    if mel.sum() > 0:
        vd[mel.astype(bool)] = np.minimum(vd.min() * 0.8, - 0.2 * vel_a)

    # Scale parameters
    if remove_trend_vt:
        vt *= controller_p
    else:
        vt = vt ** controller_p
    vd *= controller_p
    lbpr *= controller_p
    tim *= controller_p
    lart *= controller_p

    if ped is not None:
        ped = ped * (controller_p > 0)

    return vt, vd, lbpr, tim, lart, ped, mel
