"""Command-line application wrapper with configuration and daemonization
support.

"""
__version__ = '1.7.6'

import collections
import daemon
import grp
import lockfile
import logging
import optparse
import os
import platform
import pwd
import signal
import sys
import time
import traceback
import warnings
import yaml

LOGGER = logging.getLogger(__name__)

# Conditionally import the module needed for dictConfig
(major, minor, rev) = platform.python_version_tuple()
if float('%s.%s' % (major, minor)) < 2.7:
    from logutils import dictconfig as logging_config
else:
    from logging import config as logging_config

# Used to hold a global instance of the logging object
LOGGING_OBJ = None

APPNAME = 'clihelper'
APPLICATION = 'Application'
DAEMON = 'Daemon'
LOGGING = 'Logging'
CONFIG_KEYS = [APPLICATION, DAEMON, LOGGING]
CONFIG_FILE = None
CONTROLLER = None
DESCRIPTION = 'Command Line Daemon'
PIDFILE = '/var/run/%(app)s.pid'
VERSION = __version__

#: The full path to the exception log file for unwritten exceptions
EXCEPTION_LOG = '/tmp/clihelper-exceptions.log'

#: Change to False to not write unhandled exceptions to the EXCEPTION_LOG file
WRITE_EXCEPTION_LOG = True

#: Default Logging Format for Console
DEFAULT_FORMAT = ('%(levelname) -10s %(asctime)s %(process)-6d %(processName) '
                  '-15s %(threadName)-10s %(name) -25s %(funcName) -25s'
                  'L%(lineno)-6d: %(message)s')

#: Default Logging configuration
LOGGING_DEFAULT = {'disable_existing_loggers': True,
                   'filters': dict(),
                   'formatters': {'verbose': {'datefmt': '%Y-%m-%d %H:%M:%S',
                                              'format': DEFAULT_FORMAT}},
                   'handlers': {'console': {'class': 'logging.StreamHandler',
                                            'debug_only': True,
                                            'formatter': 'verbose'}},
                   'incremental': False,
                   'loggers': {'clihelper': {'handlers': ['console'],
                                             'level': 'INFO',
                                             'propagate': True}},
                   'root': {'handlers': [],
                            'level': logging.CRITICAL,
                            'propagate': True},
                   'version': 1}


class Controller(object):
    """Extend this class to implement your core application controller. Key
    methods to implement are Controller.setup, Controller.process and
    Controller.cleanup.

    If you do not want to use the sleep/wake structure but rather something
    like a blocking IOLoop, overwrite the Controller.run method.

    """
    #: When shutting down, how long should sleeping block the interpreter while
    #: waiting for the state to indicate the class is no longer active.
    SLEEP_UNIT = 0.5

    #: How often should :meth:`Controller.process` be invoked
    WAKE_INTERVAL = 60

    #: Initializing state is only set during initial object creation
    STATE_INITIALIZING = 0x01

    #: When clihelper has set the signal timer and is paused, it will be in the
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

    def __init__(self, options, arguments):
        """Create an instance of the controller passing in the debug flag,
        the options and arguments from the cli parser.

        :param optparse.Values options: OptionParser option values
        :param list arguments: Left over positional cli arguments

        """
        # Carry debug around for when/if HUP is called or the value is needed
        self._debug = options.foreground

        # Initial state setup
        self._state = None

        # Default state
        self.set_state(self.STATE_INITIALIZING)

        # Carry these for possible later use
        self._options = options
        self._arguments = arguments

        # Create a new instance of a configuration object
        self._config = get_configuration()

    @property
    def application_config(self):
        """Return the appplication section of the configuration

        :rtype: dict

        """
        return self._config.get(APPLICATION)

    def cleanup(self):
        """Override this method to cleanly shutdown the application."""
        LOGGER.debug('Unextended %s.cleanup() method', self.__class__.__name__)
        if hasattr(self, '_cleanup'):
            warnings.warn('Controller._cleanup is deprecated, '
                          'extend Controller.cleanup',
                          DeprecationWarning, stacklevel=2)
            self._cleanup()

    @property
    def config(self):
        """Property method that returns the full configuration as a dict with
        the top-level Application, Daemon, and Logging sections.

        :rtype: dict

        """
        return self._config

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

    @property
    def logging_config(self):
        """Return the logging section of the configuration file as a dict.

        :rtype: dict

        """
        return get_logging_config()

    def on_sighup(self):
        """Called when SIGHUP is received, shutdown internal runtime state,
        reloads configuration and then calls Controller.run(). Can be extended
        to implement other behaviors.

        """
        LOGGER.info('Received SIGHUP, restarting internal state')
        if hasattr(self, '_on_sighup'):
            warnings.warn('Controller._on_sighup is deprecated, '
                          'extend Controller.on_sighup',
                          DeprecationWarning, stacklevel=2)
            return self._on_sighup()
        else:
            self.stop()
            self.reload_configuration()
            self.run()

    def on_sigterm(self):
        """Called when SIGTERM is received, calling self.stop(). Override to
        implement a different behavior.

        """
        LOGGER.info('Received SIGTERM, initiating shutdown')
        if hasattr(self, '_on_sigterm'):
            warnings.warn('Controller._on_sigterm is deprecated, '
                          'extend Controller.on_sigterm',
                          DeprecationWarning, stacklevel=2)
            return self._on_sigterm()
        else:
            self.stop()

    def on_sigusr1(self):
        """Called when SIGUSR1 is received. Reloads configuration and reruns
        the LOGGER/logging setup. Override to implement a different behavior.

        """
        LOGGER.info('Received SIGUSR1, reloading configuration')

        if hasattr(self, '_on_sigusr1'):
            warnings.warn('Controller._on_sigusr1 is deprecated, '
                          'extend Controller.on_sigusr1',
                          DeprecationWarning, stacklevel=2)
            return self._on_sigusr1()
        else:
            self.reload_configuration()

            # If the app is sleeping cause it to go back to sleep
            if self.is_sleeping:
                signal.pause()

    def on_sigusr2(self):
        """Called when SIGUSR2 is received, does not have any attached
        behavior. Override to implement a behavior for this signal.

        """
        LOGGER.info('Received SIGUSR2')

        if hasattr(self, '_on_sigusr2'):
            warnings.warn('Controller._on_sigusr2 is deprecated, '
                          'extend Controller.on_sigusr2',
                          DeprecationWarning, stacklevel=2)
            return self._on_sigusr2()
        else:
            # If the app is sleeping cause it to go back to sleep
            if self.is_sleeping:
                signal.pause()

    def process(self):
        """To be implemented by the extending class. Is called after every
        sleep interval in the main application loop.

        """
        if hasattr(self, '_process'):
            warnings.warn('Controller._process is deprecated, '
                          'extend Controller.process',
                          DeprecationWarning, stacklevel=2)
            return self._process()
        raise NotImplementedError

    def reload_configuration(self):
        """Reload the configuration by creating a new instance of the
        Configuration object and re-setup logging. Extend behavior by
        overriding object while calling super to ensure the internal config
        variables are populated correctly.

        """
        # Delete the config object, creating a new one
        del self._config
        self._config = get_configuration()
        setup_logging(self._debug)

    def run(self):
        """The core method for starting the application. Will setup logging,
        toggle the runtime state flag, block on loop, then call shutdown.

        Redefine this method if you intend to use an IO Loop or some other
        long running process.

        """
        LOGGER.info('%s %s started', APPNAME, VERSION)
        self.setup()
        self.process()
        signal.signal(signal.SIGALRM, self._wake)
        self._sleep()
        while self.is_running or self.is_sleeping:
            signal.pause()

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
        if hasattr(self, '_setup'):
            warnings.warn('Controller._setup is deprecated, '
                          'extend Controller.setup',
                          DeprecationWarning, stacklevel=2)
            return self._setup()

    def stop(self):
        """Override to implement shutdown steps."""
        LOGGER.info('Attempting to stop the process')
        self.set_state(self.STATE_STOP_REQUESTED)

        # Clear out the timer
        signal.setitimer(signal.ITIMER_PROF, 0, 0)

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
    def wake_interval(self):
        """Property method that returns the wake interval in seconds.

        :rtype: int

        """
        return self.application_config.get('wake_interval', self.WAKE_INTERVAL)

    def _get_application_config(self):
        """Get the configuration data the application itself

        :rtype: dict

        """
        warnings.warn("Deprecated, use application_config property",
                      DeprecationWarning, stacklevel=2)
        return self.application_config

    def _get_config(self, key, default=None):
        """Get the configuration data for the specified key

        :param str key: The key to get config data for
        :rtype: any

        """
        warnings.warn("Deprecated, use  Controller.config property",
                      DeprecationWarning, stacklevel=2)
        return self.application_config.get(key, default)

    def _get_wake_interval(self):
        """Return the wake interval in seconds.

        :rtype: int

        """
        warnings.warn("Deprecated, use wake_interval property",
                      DeprecationWarning, stacklevel=2)
        return self.wake_interval

    def _set_state(self, value):
        """Deprecated method to be removed"""
        warnings.warn('Deprecated, use Controller.set_state instead',
                      DeprecationWarning, stacklevel=2)
        self.set_state(value)

    def _shutdown(self):
        """Deprecated method to be removed"""
        warnings.warn('Deprecated, use Controller.stop instead',
                      DeprecationWarning, stacklevel=2)
        self.stop()

    def _shutdown_complete(self):
        """Deprecated method to be removed"""
        warnings.warn('Deprecated, use Controller.stopped instead',
                      DeprecationWarning, stacklevel=2)
        self._stopped()

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


class Logging(object):
    """The Logging class is used for abstracting away dictConfig logging
    semantics and can be used by sub-processes to ensure consistent logging
    rule application.

    """
    DEBUG_ONLY = 'debug_only'
    HANDLERS = 'handlers'
    LOGGERS = 'loggers'

    def __init__(self, configuration, debug):
        """Create a new instance of the Logging object passing in the
        DictConfig syntax logging configuration and a debug flag.

        :param dict configuration: The logging configuration
        :param bool debug: Toggles use of debug_only loggers

        """
        self.set_configuration(configuration, debug)
        try:
            logging.captureWarnings(True)
        except AttributeError:
            pass

    def configure(self):
        """Configure the Python logging runtime with the configuration values
        passed in when creating the object.

        """
        LOGGER.debug('Updating logging config via dictConfig')
        logging_config.dictConfig(self.config)

    def set_configuration(self, configuration, debug):
        """Update the internal configuration values, removing debug_only
        handlers if debug is False.

        :param dict configuration: The logging configuration
        :param bool debug: Toggles use of debug_only loggers

        """
        self.config = configuration
        if not debug:
            self._remove_debug_only_handlers()
        self._remove_debug_only_from_handlers()

    def _remove_debug_only_from_handlers(self):
        """Iterate through each handler removing the invalid dictConfig key of
        debug_only.

        """
        LOGGER.debug('Removing debug only from handlers')
        for handler in self.config[self.HANDLERS]:
            if self.DEBUG_ONLY in self.config[self.HANDLERS][handler]:
                del self.config[self.HANDLERS][handler][self.DEBUG_ONLY]

    def _remove_debug_only_handlers(self):
        """Remove any handlers with an attribute of debug_only that is True and
        remove the references to said handlers from any loggers that are
        referencing them.

        """
        LOGGER.debug('Removing debug only handlers')
        remove = list()
        for handler in self.config[self.HANDLERS]:
            if self.config[self.HANDLERS][handler].get('debug_only'):
                remove.append(handler)
        for handler in remove:
            del self.config[self.HANDLERS][handler]

            for logger in self.config[self.LOGGERS].keys():
                logger = self.config[self.LOGGERS][logger]
                if handler in logger[self.HANDLERS]:
                    logger[self.HANDLERS].remove(handler)

        self._remove_debug_only_from_handlers()


def add_config_key(key):
    """Add a top-level key to the expected configuration values for validation

    :param str key: The key to add to the configuration keys

    """
    global CONFIG_KEYS
    CONFIG_KEYS.append(key)


def get_logging_config():
    """Return the configuration data for dictConfig

    :rtype: dict

    """
    logging_config = _merge_dicts(LOGGING_DEFAULT,
                                  get_configuration().get(LOGGING, dict()))
    return logging_config


def get_configuration():
    """Return the configuration object, validating that the required top-level
    keys exists.

    :rtype: dict

    """
    # Load the configuration file from disk
    configuration = _load_config()

    # Validate all the top-level items are there
    for key in CONFIG_KEYS:
        if key not in configuration:
            raise ValueError('Missing required configuration parameter: %s',
                             key)

    # Return the configuration dictionary
    return configuration


def run(controller, option_callback=None):
    """Called by the implementing application to run the application.
    ControllerClass is a class that extends clihelper.Controller.

    :param Controller controller: Implementing class extending Controller
    :param method option_callback: If passed, is called after the foreground
                                   option is added to the option parser
                                   parameters.

    """
    options, arguments = _cli_options(option_callback)

    # Setup the config file
    try:
        set_configuration_file(options.configuration)
    except ValueError as error:
        sys.stderr.write('Error: %s\n' % error)
        sys.exit(1)

    # Run the process with the daemon context
    kwargs = _get_daemon_context_kargs(options.foreground)
    if options.foreground:
        kwargs['detach_process'] = False
        kwargs['stderr'] = sys.stderr
        kwargs['stdin'] = sys.stdin
        kwargs['stdout'] = sys.stdout
        kwargs['working_directory'] = os.getcwd()

    # This will be used by the caller to daemonize the application
    try:
        with daemon.DaemonContext(**kwargs):
            setup_logging(options.foreground)
            process = controller(options, arguments)
            set_controller(process)
            if not options.foreground:
                _write_pidfile()
            try:
                process.run()
            except KeyboardInterrupt:
                LOGGER.info('CTRL-C caught, shutting down')
                process.stop()
            if not options.foreground:
                _remove_pidfile()
    except Exception as error:
        if WRITE_EXCEPTION_LOG:
            sys.stdout.write('Exception: %r\n\n' % error)
            with open(EXCEPTION_LOG, 'a') as handle:
                output = traceback.format_exception(*sys.exc_info())
                _dev_null = [(handle.write(line),
                             sys.stdout.write(line)) for line in output]
        if not options.foreground:
            _remove_pidfile()
        sys.exit(1)

    LOGGER.info('clihelper.run exiting cleanly')


def set_appname(appname):
    """Sets the application name for the instance of the application.

    :param str appname: The application name

    """
    global APPNAME
    APPNAME = appname


def set_configuration_file(filename):
    """Sets the path for the configuration file.

    :param str filename: The full path to the configuration file
    :raises: ValueError

    """
    global CONFIG_FILE

    # Make sure the configuration file was specified
    if not filename:
        sys.stderr.write('Missing required configuration file value\n')
        sys.exit(1)

    filename = os.path.abspath(filename)
    if not os.path.exists(filename):
        sys.stderr.write('Configuration file "%s" does not exist\n' %
                         filename)
        sys.exit(1)

    # Set the config file to the global variable
    CONFIG_FILE = filename


def set_controller(controller):
    """Sets the controller for the instance of the application.

    :param Controller controller: The Controller object

    """
    global CONTROLLER
    CONTROLLER = controller


def set_description(description):
    """Sets the description for the instance of the application.

    :param str description: The app description

    """
    global DESCRIPTION
    DESCRIPTION = description


def set_version(version):
    """Sets the version for the instance of the application.

    :param str version: The version #

    """
    global VERSION
    VERSION = version


def setup(appname, description, version):
    """Setup the application with one method instead of calling all four.

    :param str appname: The application name
    :param str description: The app description
    :param str version: The version #

    """
    set_appname(appname)
    set_description(description)
    set_version(version)


def setup_logging(debug):
    """Setup the logging configuration and assign the LOGGER. If debug is False
    strip any handlers and their references from the configuration.

    :param bool debug: The app is in debug mode

    """
    global LOGGING_OBJ
    if not LOGGING_OBJ:
        LOGGING_OBJ = Logging(get_logging_config(), debug)
    else:
        LOGGING_OBJ.set_configuration(get_logging_config(), debug)
    LOGGING_OBJ.configure()


# Internal Methods

def _cli_options(option_callback):
    """Setup the option parser and return the options and arguments.

    :param method option_callback: If passed, is called after the foreground
                                   option is added to the option parser
                                   parameters. The parser will be passed
                                   as an argument to the callback.
    :rtype tuple: optparse.Values, list

    """
    parser = _new_option_parser()

    # Set default attributes
    parser.usage = "usage: %prog -c <configfile> [options]"
    parser.version = "%%prog v%s" % VERSION
    parser.description = DESCRIPTION

    # Add default options
    parser.add_option("-c", "--config",
                      action="store",
                      dest="configuration",
                      default=False,
                      help="Path to the configuration file")

    parser.add_option("-f", "--foreground",
                      action="store_true",
                      dest="foreground",
                      default=False,
                      help="Run interactively in console")

    # If the option callback is specified, call it with the parser instance
    if option_callback:
        option_callback(parser)

    # Parse our options and arguments
    return parser.parse_args()


def _get_daemon_config():
    """Return the daemon specific configuration values

    :rtype: dict

    """
    return get_configuration().get(DAEMON) or dict()


def _get_daemon_context_kargs(foreground=False):
    """Return pre-configured keyword arguments for the DaemonContext

    :rtype: dict

    """
    config = _get_daemon_config()
    uid, gid = None, None
    if foreground:
        LOGGER.info('Running interactively, not switching user or group')
    else:
        if config.get('user'):
            uid = _get_uid(config['user'])
        if config.get('group'):
            gid = _get_gid(config['group'])

    kwargs = {'detach_process': not foreground,
              'gid': gid,
              'prevent_core': config.get('prevent_core', foreground),
              'signal_map': {signal.SIGHUP: _on_sighup,
                             signal.SIGTERM: _on_sigterm,
                             signal.SIGUSR1: _on_sigusr1,
                             signal.SIGUSR2: _on_sigusr2},
              'uid': uid}
    if not foreground:
        kwargs['pidfile'] = lockfile.FileLock(path=_get_pidfile_path())
    return kwargs


def _get_gid(group):
    """Return the group id for the specified group.

    :param str group: The group name to get the id for
    :rtype: int

    """
    return grp.getgrnam(group).gr_gid


def _get_pidfile_path():
    """Return the pidfile path for the daemon context.

    :rtype: str

    """
    config = _get_daemon_config()
    return config.get('pidfile', PIDFILE) % {'app': APPNAME}


def _get_uid(username):
    """Return the user id for the specified username

    :param str username: The user to get the UID for
    :rtype: int

    """
    return pwd.getpwnam(username).pw_uid


def _load_config():
    """Load the configuration from disk returning a dictionary object
    representing the configuration values.

    :rtype: dict
    :raises: OSError

    """
    return _parse_yaml(_read_config_file())


def _merge_dicts(d, u):
    """Merge two nested dictionaries, stolen from
            http://stackoverflow.com/questions/3232943

    :param dict d: First dict to merge
    :param dict u: Second dict to merge
    :rtype: dict

    """
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = _merge_dicts(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def _new_option_parser():
    """Return a new optparse.OptionParser instance.

    :rtype: optparse.OptionParser

    """
    return optparse.OptionParser()


def _on_sighup(_signal, _frame):
    """Received when SIGHUP is received.

    :param int _signal: The signal number
    :param frame _frame: The stack frame when received

    """
    LOGGER.debug('SIGHUP received, notifying controller')
    CONTROLLER.on_sighup()


def _on_sigterm(_signal, _frame):
    """Received when SIGTERM is received.

    :param int _signal: The signal number
    :param frame _frame: The stack frame when received

    """
    LOGGER.debug('SIGTERM received, notifying controller')
    CONTROLLER.on_sigterm()


def _on_sigusr1(_signal, _frame):
    """Received when SIGUSR1 is received.

    :param int _signal: The signal number
    :param frame _frame: The stack frame when received

    """
    LOGGER.debug('SIGUSR1 received, notifying controller')
    CONTROLLER.on_sigusr1()


def _on_sigusr2(_signal, _frame):
    """Received when SIGUSR2 is received.

    :param int _signal: The signal number
    :param frame _frame: The stack frame when received

    """
    LOGGER.debug('SIGUSR2 received, notifying controller')
    CONTROLLER.on_sigusr2()


def _parse_yaml(content):
    """Parses a YAML string and returns a dictionary object.

    :param str content: The YAML content
    :rtype: dict

    """
    return yaml.safe_load(content)


def _read_config_file():
    """Return the contents of the file specified in _CONFIG_FILE.

    :rtype: str

    """
    with open(CONFIG_FILE, 'r') as handle:
        return handle.read()


def _remove_file(path):
    try:
        if os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass

def _remove_pidfile():
    """Remove the pidfile from the filesystem"""
    _remove_file(_get_pidfile_path())
    _remove_pidlock_file()

def _remove_pidlock_file():
    """Remove the pid lock file from the filesystem"""
    _remove_file("%s.lock" % _get_pidfile_path())

def _write_pidfile():
    """Write the pidfile out with the process number in the pidfile"""
    with open(_get_pidfile_path(), "w") as handle:
        handle.write(str(os.getpid()))
