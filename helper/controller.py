"""
Helper Controller Class

"""
import logging
import os
import platform
import signal
import sys
import time

from helper import config
from helper import __version__

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
    _STATES = {0x01: 'Initializing',
               0x02: 'Sleeping',
               0x03: 'Idle',
               0x04: 'Active',
               0x05: 'Stop Requested',
               0x06: 'Stopping',
               0x07: 'Stopped'}

    # Default state
    _state = None

    def __init__(self, args, operating_system):
        """Create an instance of the controller passing in the debug flag,
        the options and arguments from the cli parser.

        :param argparse.Namespace args: Command line arguments
        :param str operating_system: Operating system name from helper.platform

        """
        self.set_state(self.STATE_INITIALIZING)
        self.args = args
        self.debug = args.foreground
        try:
            self.config = config.Config(args.config)
        except ValueError:
            sys.exit(1)
        self.logging_config = config.LoggingConfig(self.config.logging,
                                                   self.debug)
        self.operating_system = operating_system

    def cleanup(self):
        """Override this method to cleanly shutdown the application."""
        LOGGER.debug('Unextended %s.cleanup() method', self.__class__.__name__)

    def configuration_reloaded(self):
        """Override to provide any steps when the configuration is reloaded."""
        LOGGER.debug('Unextended %s.configuration_reloaded() method',
                     self.__class__.__name__)

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

    def on_sighup(self, signum_unused, frame_unused):
        """Called when SIGHUP is received, shutdown internal runtime state,
        reloads configuration and then calls Controller.run(). Can be extended
        to implement other behaviors.

        """
        LOGGER.info('Received SIGHUP')
        if self.config.reload():
            LOGGER.info('Configuration reloaded')
            if self.logging_config.update(self.config.logging, self.debug):
                LOGGER.info('Logging configuration updated')
            self.configuration_reloaded()

        if self.is_sleeping:
            signal.pause()

    def on_sigterm(self, signum_unused, frame_unused):
        """Called when SIGTERM is received, calling self.stop(). Override to
        implement a different behavior.

        """
        LOGGER.info('Received SIGTERM, initiating shutdown')
        self.stop()

    def on_sigusr1(self, signum_unused, frame_unused):
        """Called when SIGUSR1 is received, does not have any attached
        behavior. Override to implement a behavior for this signal.

        """
        LOGGER.info('Received SIGUSR1')

    def on_sigusr2(self, signum_unused, frame_unused):
        """Called when SIGUSR2 is received, does not have any attached
        behavior. Override to implement a behavior for this signal.

        """
        LOGGER.info('Received SIGUSR2')

    def process(self):
        """To be implemented by the extending class. Is called after every
        sleep interval in the main application loop.

        """
        raise NotImplementedError

    def run(self):
        """The core method for starting the application. Will setup logging,
        toggle the runtime state flag, block on loop, then call shutdown.

        Redefine this method if you intend to use an IO Loop or some other
        long running process.

        """
        LOGGER.info('%s v%s started', self.APPNAME, self.VERSION)
        self.setup()
        self.process()
        signal.signal(signal.SIGALRM, self._wake)
        self._sleep()
        while self.is_running or self.is_sleeping:
            signal.pause()

    def start(self):
        """Important:

            Do not extend this method, rather redefine Controller.run

        """
        self.setup_signals()
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
        LOGGER.debug('Attempting to set state to %s', self._STATES.get(state,
                                                                       state))
        if state == self._state:
            LOGGER.debug('Ignoring request to set state to current state: %s',
                         self._STATES[state])
            return

        if state not in self._STATES.keys():
            raise ValueError('Invalid Runtime State')

        if self.is_waiting_to_stop and state not in [self.STATE_STOPPING,
                                                     self.STATE_STOPPED]:
            LOGGER.warning('Attempt to set invalid state while waiting to '
                           'shutdown: %s ', self._STATES[state])
            return

        # Validate the next state for a shutting down process
        if self.is_stopping and state != self.STATE_STOPPED:
            LOGGER.warning('Attempt to set invalid post shutdown state: %s',
                           self._STATES[state])
            return

        # Validate the next state for a running process
        if self.is_running and state not in [self.STATE_ACTIVE,
                                             self.STATE_IDLE,
                                             self.STATE_SLEEPING,
                                             self.STATE_STOP_REQUESTED,
                                             self.STATE_STOPPING]:
            LOGGER.warning('Attempt to set invalid post running state: %s',
                           self._STATES[state])
            return

        # Validate the next state for a sleeping process
        if self.is_sleeping and state not in [self.STATE_ACTIVE,
                                              self.STATE_IDLE,
                                              self.STATE_STOP_REQUESTED,
                                              self.STATE_STOPPING]:
            LOGGER.warning('Attempt to set invalid post sleeping state: %s',
                           self._STATES[state])
            return

        # Set the value
        self._state = state

        # Log the change
        LOGGER.debug('Runtime state changed to %s', self._STATES[self._state])

    def setup(self):
        """Override to provide any required setup steps."""
        LOGGER.debug('Unextended %s.setup() method', self.__class__.__name__)

    def setup_signals(self):
        signal.signal(signal.SIGHUP, self.on_sighup)
        signal.signal(signal.SIGTERM, self.on_sigterm)
        signal.signal(signal.SIGUSR1, self.on_sigusr1)
        signal.signal(signal.SIGUSR2, self.on_sigusr2)

    def shutdown(self):
        """Override to provide any required shutdown steps."""
        LOGGER.debug(
            'Unextended %s.shutdown() method', self.__class__.__name__)

    def stop(self):
        """Override to implement shutdown steps."""
        LOGGER.info('Attempting to stop the process')
        self.set_state(self.STATE_STOP_REQUESTED)

        # Clear out the timer
        signal.setitimer(signal.ITIMER_PROF, 0, 0)

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
        self.cleanup()

        # Change our state
        self._stopped()

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

    def _sleep(self):
        """Setup the next alarm to fire and then wait for it to fire."""
        # Make sure that the application is not shutting down before sleeping
        if self.is_stopping:
            LOGGER.debug('Not sleeping, application is trying to shutdown')
            return

        # Set the signal timer
        signal.setitimer(signal.ITIMER_REAL, self.wake_interval, 0)

        # Toggle that we are running
        self.set_state(self.STATE_SLEEPING)

    def _stopped(self):
        """Sets the state back to idle when shutdown steps are complete."""
        LOGGER.debug('Application stopped')
        self.set_state(self.STATE_STOPPED)

    def _wake(self, _signal, _frame):
        """Fired every time the alarm is signaled. If the app is not shutting
        or shutdown, it will attempt to process.

        :param int _signal: The signal number
        :param frame _frame: The stack frame when received

        """
        LOGGER.debug('Application woke up')

        # Only run the code path if it's not shutting down or shutdown
        if not any([self.is_stopping, self.is_stopped, self.is_idle]):

            # Note that we're running
            self.set_state(self.STATE_ACTIVE)

            # Process actions for the application
            self.process()

            # Exit out if the app is waiting to stop
            if self.is_waiting_to_stop:
                return self.set_state(self.STATE_STOPPING)

            # Wait until the process is to be woken again
            self._sleep()
        else:
            LOGGER.info('Exiting wake interval without sleeping again')
