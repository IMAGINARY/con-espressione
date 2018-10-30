import Leap
from kivy.uix.widget import Widget
from kivy.core.window import Window


class Controller():
    """
        Base class for input controller.
    """

    def __init__(self):
        self.last_pos = (0.5, 0.5)  # for smoothing
        self.x_lim = (0, 1)
        self.y_lim = (0, 1)

    def get_pos(self):
        raise NotImplementedError

    def limit_pos(self, pos):
        # set position limits
        new_pos = [0, 0]
        new_pos[0] = max(pos[0], self.x_lim[0])
        new_pos[0] = min(pos[0], self.x_lim[1])

        new_pos[1] = max(pos[1], self.y_lim[0])
        new_pos[1] = min(pos[1], self.y_lim[1])

        return new_pos

    def smooth(self, pos, last_pos, smoothing_factor=1.0):
        """Smooth hand trajectory with exponential moving average filter."""

        pos[0] = smoothing_factor * pos[0] + (1 - smoothing_factor) * last_pos[0]
        pos[1] = smoothing_factor * pos[1] + (1 - smoothing_factor) * last_pos[1]

        return pos


class LeapMotion(Controller):
    def __init__(self):
        Controller.__init__(self)

        # instantiate LeapMotion controller
        self.controller = Leap.Controller()

        # controller's coordinate system
        self.x_lim = (-200, 200)
        self.y_lim = (100, 400)

    def get_pos(self, smoothing_factor):
        """Get hand position from LeapMotion.

        Parameters
        ----------
        smoothing_factor : float
            Smoothing factor for the trajectory. Should lie in [0, 1]

        Returns
        -------
        pos : tuple
            Tuple with x (pos[0]) and y (pos[1]) coordinate,
            normalized to [0, 1].
        """

        # get current frame
        frame = self.controller.frame()

        # only access hand if one is available
        if len(frame.hands) > 0:
            # get the first hand
            hand = frame.hands[0]

            # extract palm position (0 ... x-axis, 1 ... y-axis, 2 ... z-axis)
            pos = [hand.palm_position[0], hand.palm_position[1]]
            pos = self.limit_pos(pos)

            # project sensor data to [0, 1]
            pos[0] = max(0, min(pos[0] / 400.0 + 0.5, 1))  # x
            pos[1] = max(0, min(pos[1] / 300.0 - 1./3, 1))  # y

            if smoothing_factor != 1.0:
                self.smooth(pos, self.last_pos, smoothing_factor)

            # update last position
            self.last_pos = pos

            return pos


class Mouse(Controller):
    def __init__(self):
        Controller.__init__(self)

        # instantiate LeapMotion controller
        self.controller = Widget()

        # controller's coordinate system
        self.x_lim = (0, Window.width)
        self.y_lim = (0, Window.height)

    def get_pos(self, smoothing_factor):
        """Get hand position from Mouse input.

        Parameters
        ----------
        smoothing_factor : float
            Smoothing factor for the trajectory. Should lie in [0, 1]

        Returns
        -------
        pos : tuple
            Tuple with x (pos[0]) and y (pos[1]) coordinate,
            normalized to [0, 1].
        """

        # get mouse position
        pos = Window.mouse_pos
        pos = self.limit_pos(pos)

        # project sensor data to [0, 1]
        pos[0] = pos[0] / self.x_lim[1]  # x
        pos[1] = pos[1] / self.y_lim[1]  # y

        if smoothing_factor != 1.0:
            self.smooth(pos, self.last_pos, smoothing_factor)

        # update last position
        self.last_pos = pos

        return pos
