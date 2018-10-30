"""
Helper Controller Class

"""
import logging
import logging.config
import os
import multiprocessing
import platform
try:
    import queue
except ImportError:
    import Queue as queue
import signal
import sys
import time

from helper import config, __version__

LOGGER = logging.getLogger(__name__)


class Controller(object):
    """Extend this class to implement your core application controller. Key
    methods to implement are Controller.setup, Controller.process and
    Controller.cleanup.

    If you do not want to use the sleep/wake structure but rather something
    like a blocking IOLoop, overwrite the Controller.run method.

    """
    APPNAME = sys.argv[0].split(os.sep)[-1]
    VERSION = __version__

    #: When shutting down, how long should sleeping block the interpreter while
    #: waiting for the state to indicate the class is no longer active.
    SLEEP_UNIT = 0.5

    #: How often should :meth:`Controller.process` be invoked
    WAKE_INTERVAL = 60

    #: Initializing state is only set during initial object creation
    STATE_INITIALIZING = 0x01

    #: When helper has set the signal timer and is paused, it will be in the
    #: sleeping state.
    STATE_SLEEPING = 0x02

    #: The idle state is available to implementing classes to indicate that
    #: while they are not actively performing tasks, they are not sleeping.
    #: Objects in the idle state can be shutdown immediately.
    STATE_IDLE = 0x03

    #: The active state should be set whenever the implementing class is
    #: performing a task that can not be interrupted.
    STATE_ACTIVE = 0x04

    #: The stop requested state is set when a signal is received indicating the
    #: process should stop. The app will invoke the :meth:`Controller.stop`
    #: method which will wait for the process state to change from STATE_ACTIVE
    STATE_STOP_REQUESTED = 0x05

    #: Once the application has started to shutdown, it will set the state to
    #: stopping and then invoke the :meth:`Controller.stopping` method.
    STATE_STOPPING = 0x06

    #: Once the application has fully stopped, the state is set to stopped.
    STATE_STOPPED = 0x07

    # For reverse lookup
    _STATES = {0x00: 'None',
               0x01: 'Initializing',
               0x02: 'Sleeping',
               0x03: 'Idle',
               0x04: 'Active',
               0x05: 'Stop Requested',
               0x06: 'Stopping',
               0x07: 'Stopped'}

    # Default state
    _state = 0x00

    def __init__(self, args, operating_system):
        """Create an instance of the controller passing in the debug flag,
        the options and arguments from the cli parser.

        :param argparse.Namespace args: Command line arguments
        :param str operating_system: Operating system name from helper.platform

        """
        self.set_state(self.STATE_INITIALIZING)
        self.args = args
        try:
            self.config = config.Config(args.config)
        except ValueError:
            sys.exit(1)
        self.debug = args.foreground
        logging.config.dictConfig(self.config.logging)
        self.operating_system = operating_system
        self.pending_signals = multiprocessing.Queue()

    @property
    def current_state(self):
        """Property method that return the string description of the runtime
        state.

        :rtype: str

        """
        return self._STATES[self._state]

    @property
    def is_active(self):
        """Property method that returns a bool specifying if the process is
        currently active.

        :rtype: bool

        """
        return self._state == self.STATE_ACTIVE

    @property
    def is_idle(self):
        """Property method that returns a bool specifying if the process is
        currently idle.

        :rtype: bool

        """
        return self._state == self.STATE_IDLE

    @property
    def is_initializing(self):
        """Property method that returns a bool specifying if the process is
        currently initializing.

        :rtype: bool

        """
        return self._state == self.STATE_INITIALIZING

    @property
    def is_running(self):
        """Property method that returns a bool specifying if the process is
        currently running. This will return true if the state is active, idle
        or initializing.

        :rtype: bool

        """
        return self._state in [self.STATE_ACTIVE,
                               self.STATE_IDLE,
                               self.STATE_INITIALIZING]

    @property
    def is_sleeping(self):
        """Property method that returns a bool specifying if the process is
        currently sleeping.

        :rtype: bool

        """
        return self._state == self.STATE_SLEEPING

    @property
    def is_stopped(self):
        """Property method that returns a bool specifying if the process is
        stopped.

        :rtype: bool

        """
        return self._state == self.STATE_STOPPED

    @property
    def is_stopping(self):
        """Property method that returns a bool specifying if the process is
        stopping.

        :rtype: bool

        """
        return self._state == self.STATE_STOPPING

    @property
    def is_waiting_to_stop(self):
        """Property method that returns a bool specifying if the process is
        waiting for the current process to finish so it can stop.

        :rtype: bool

        """
        return self._state == self.STATE_STOP_REQUESTED

    def on_configuration_reloaded(self):
        """Override to provide any steps when the configuration is reloaded."""
        LOGGER.debug('%s.on_configuration_reloaded() NotImplemented',
                     self.__class__.__name__)

    def on_shutdown(self):
        """Override this method to cleanly shutdown the application."""
        LOGGER.debug('%s.cleanup() NotImplemented', self.__class__.__name__)

    def on_sigusr1(self):
        """Called when SIGUSR1 is received, does not have any attached
        behavior. Override to implement a behavior for this signal.

        """
        LOGGER.debug('%s.on_sigusr1() NotImplemented', self.__class__.__name__)

    def on_sigusr2(self):
        """Called when SIGUSR2 is received, does not have any attached
        behavior. Override to implement a behavior for this signal.

        """
        LOGGER.debug('%s.on_sigusr2() NotImplemented', self.__class__.__name__)

    def process(self):
        """To be implemented by the extending class. Is called after every
        sleep interval in the main application loop.

        """
        raise NotImplementedError

    def process_signal(self, signum):
        """Invoked whenever a signal is added to the stack.

        :param int signum: The signal that was added

        """
        if signum == signal.SIGTERM:
            LOGGER.info('Received SIGTERM, initiating shutdown')
            self.stop()
        elif signum == signal.SIGHUP:
            LOGGER.info('Received SIGHUP')
            if self.config.reload():
                LOGGER.info('Configuration reloaded')
                logging.config.dictConfig(self.config.logging)
                self.on_configuration_reloaded()
        elif signum == signal.SIGUSR1:
            self.on_sigusr1()
        elif signum == signal.SIGUSR2:
            self.on_sigusr2()

    def run(self):
        """The core method for starting the application. Will setup logging,
        toggle the runtime state flag, block on loop, then call shutdown.

        Redefine this method if you intend to use an IO Loop or some other
        long running process.

        """
        LOGGER.info('%s v%s started', self.APPNAME, self.VERSION)
        self.setup()
        while not any([self.is_stopping, self.is_stopped]):
            self.set_state(self.STATE_SLEEPING)
            try:
                signum = self.pending_signals.get(True, self.wake_interval)
            except queue.Empty:
                pass
            else:
                self.process_signal(signum)
                if any([self.is_stopping, self.is_stopped]):
                    break
            self.set_state(self.STATE_ACTIVE)
            self.process()

    def start(self):
        """Important:

            Do not extend this method, rather redefine Controller.run

        """
        for signum in [signal.SIGHUP, signal.SIGTERM,
                       signal.SIGUSR1, signal.SIGUSR2]:
            signal.signal(signum, self._on_signal)
        self.run()

    def set_state(self, state):
        """Set the runtime state of the Controller. Use the internal constants
        to ensure proper state values:

        - :attr:`Controller.STATE_INITIALIZING`
        - :attr:`Controller.STATE_ACTIVE`
        - :attr:`Controller.STATE_IDLE`
        - :attr:`Controller.STATE_SLEEPING`
        - :attr:`Controller.STATE_STOP_REQUESTED`
        - :attr:`Controller.STATE_STOPPING`
        - :attr:`Controller.STATE_STOPPED`

        :param int state: The runtime state
        :raises: ValueError

        """
        if state == self._state:
            return
        elif state not in self._STATES.keys():
            raise ValueError('Invalid state {}'.format(state))

        # Check for invalid transitions

        if self.is_waiting_to_stop and state not in [self.STATE_STOPPING,
                                                     self.STATE_STOPPED]:
            LOGGER.warning('Attempt to set invalid state while waiting to '
                           'shutdown: %s ', self._STATES[state])
            return

        elif self.is_stopping and state != self.STATE_STOPPED:
            LOGGER.warning('Attempt to set invalid post shutdown state: %s',
                           self._STATES[state])
            return

        elif self.is_running and state not in [self.STATE_ACTIVE,
                                               self.STATE_IDLE,
                                               self.STATE_SLEEPING,
                                               self.STATE_STOP_REQUESTED,
                                               self.STATE_STOPPING]:
            LOGGER.warning('Attempt to set invalid post running state: %s',
                           self._STATES[state])
            return

        elif self.is_sleeping and state not in [self.STATE_ACTIVE,
                                                self.STATE_IDLE,
                                                self.STATE_STOP_REQUESTED,
                                                self.STATE_STOPPING]:
            LOGGER.warning('Attempt to set invalid post sleeping state: %s',
                           self._STATES[state])
            return

        LOGGER.debug('State changed from %s to %s',
                     self._STATES[self._state], self._STATES[state])
        self._state = state

    def setup(self):
        """Override to provide any required setup steps."""
        LOGGER.debug('%s.setup() NotImplemented', self.__class__.__name__)

    def shutdown(self):
        """Override to provide any required shutdown steps."""
        LOGGER.debug('%s.shutdown() NotImplemented', self.__class__.__name__)

    def stop(self):
        """Override to implement shutdown steps."""
        LOGGER.info('Attempting to stop the process')
        self.set_state(self.STATE_STOP_REQUESTED)

        # Call shutdown for classes to add shutdown steps
        self.shutdown()

        # Wait for the current run to finish
        while self.is_running and self.is_waiting_to_stop:
            LOGGER.info('Waiting for the process to finish')
            time.sleep(self.SLEEP_UNIT)

        # Change the state to shutting down
        if not self.is_stopping:
            self.set_state(self.STATE_STOPPING)

        # Call a method that may be overwritten to cleanly shutdown
        self.on_shutdown()

        # Change our state
        self.set_state(self.STATE_STOPPED)

    @property
    def system_platform(self):
        """Return a tuple containing the operating system, python
        implementation (CPython, pypy, etc), and python version.

        :rtype: tuple(str, str, str)

        """
        return (self.operating_system,
                platform.python_implementation(),
                platform.python_version())

    @property
    def wake_interval(self):
        """Property method that returns the wake interval in seconds.

        :rtype: int

        """
        return (self.config.application.get('wake_interval') or
                self.WAKE_INTERVAL)

    def _on_signal(self, signum, _frame):
        """Append the signal to the queue, to be processed by the main."""
        self.pending_signals.put(signum)
