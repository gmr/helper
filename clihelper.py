"""Command-line application wrapper with configuration and daemonization
support.

"""
__author__ = 'Gavin M. Roy'
__email__ = 'gmr@meetme.com'
__since__ = '2012-04-11'
__version__ = '1.5.1'

import daemon
import grp
import lockfile
import logging
try:
    from logging.config import dictConfig
except ImportError:
    from logutils.dictconfig import dictConfig
import optparse
import os
import pwd
import signal
import sys
import time
import traceback
import yaml

_APPNAME = 'clihelper'
_APPLICATION = 'Application'
_DAEMON = 'Daemon'
_LOGGING = 'Logging'
_CONFIG_KEYS = [_APPLICATION, _DAEMON, _LOGGING]
_CONFIG_FILE = None
_CONTROLLER = None
_DESCRIPTION = 'Command Line Daemon'
_PIDFILE = '/var/run/%(app)s.pid'

LOGGER = logging.getLogger(__name__)


class Controller(object):
    """Extend the Controller class with your own application implementing the
    Controller._process method. If you do not want to use sleep based looping
    but rather an IOLoop or some other long-lived blocking loop, redefine
    the Controller._loop method.

    """
    _SLEEP_UNIT = 0.5
    _WAKE_INTERVAL = 60  # How many seconds to sleep before waking up

    _STATE_IDLE = 0
    _STATE_RUNNING = 1
    _STATE_SLEEPING = 2
    _STATE_SHUTTING_DOWN = 3

    def __init__(self, options, arguments):
        """Create an instance of the controller passing in the debug flag,
        the options and arguments from the cli parser.

        :param optparse.Values options: OptionParser option values
        :param list arguments: Left over positional cli arguments

        """
        self._state = None

        # Default state
        self._set_state(self._STATE_IDLE)

        # Carry these for possible later use
        self._options = options
        self._arguments = arguments

        # Carry debug around for when/if HUP is called or the value is needed
        self._debug = options.foreground

        # Create a new instance of a configuration object
        self._config = get_configuration()

        # Write out the pidfile
        self._write_pidfile()

    def _cleanup(self):
        """Override this method to cleanly shutdown."""
        LOGGER.debug('Unextended %s._cleanup() method', self.__class__.__name__)

    def _get_application_config(self):
        """Get the configuration data the application itself

        :rtype: dict

        """
        return self._config.get(_APPLICATION)

    def _get_config(self, key):
        """Get the configuration data for the specified key

        :param str key: The key to get config data for
        :rtype: any

        """
        return self._get_application_config().get(key)

    def _get_wake_interval(self):
        """Return the wake interval in seconds.

        :rtype: int

        """
        interval = self._get_application_config().get('wake_interval',
                                                      self._WAKE_INTERVAL)
        LOGGER.debug('Wake interval set to %i seconds', interval)
        return interval

    def _on_sighup(self):
        """Called when SIGHUP is received, shutdown internal runtime state,
        reloads configuration and then calls Controller.run().

        """
        LOGGER.info('Received SIGHUP, restarting internal state')
        self._shutdown()
        self._reload_configuration()
        self.run()

    def _on_sigterm(self):
        """Called when SIGTERM is received, override to implement."""
        LOGGER.info('Received SIGTERM, initiating shutdown')
        self._shutdown()

    def _on_sigusr1(self):
        """Called when SIGUSR1 is received. Reloads configuration and reruns
        the LOGGER/logging setup.

        """
        LOGGER.info('Received SIGUSR1, reloading configuration')
        self._reload_configuration()

        # If the app is sleeping wait for the signal to call _wake
        if self.is_sleeping:
            signal.pause()

    def _on_sigusr2(self):
        """Called when SIGUSR2 is received, override to implement."""
        LOGGER.info('Received SIGUSR2')

        # If the app is sleeping wait for the signal to call _wake
        if self.is_sleeping:
            signal.pause()

    def _process(self):
        """To be implemented by the extending class. Is called after every sleep
        interval in the main application loop.

        """
        raise NotImplementedError

    def _reload_configuration(self):
        """Reload the configuration by creating a new instance of the
        Configuration object and re-setup logging. Extend behavior by
        overriding object while calling super.

        """
        # Delete the config object, creating a new one
        del self._config
        self._config = get_configuration()

        # Re-Setup logging
        setup_logging(self._debug)

    def _set_state(self, state):
        """Set the runtime state of the Controller.

        :param int state: The runtime state
        :raises: ValueError

        """
        LOGGER.debug('Attempting to set state to %i', state)

        if state not in [self._STATE_IDLE,
                         self._STATE_RUNNING,
                         self._STATE_SLEEPING,
                         self._STATE_SHUTTING_DOWN]:
            raise ValueError('Invalid Runtime State')

        # Validate the next state for a shutting down process
        if self.is_shutting_down and state != self._STATE_IDLE:
            LOGGER.warning('Attempt to set invalid post shutdown state: %i',
                           state)
            return

        # Validate the next state for a running process
        if self.is_running and state not in [self._STATE_SLEEPING,
                                             self._STATE_SHUTTING_DOWN]:
            LOGGER.warning('Attempt to set invalid post running state: %i',
                           state)
            return

        # Validate the next state for a sleeping process
        if self.is_sleeping and state not in [self._STATE_RUNNING,
                                              self._STATE_SHUTTING_DOWN]:
            LOGGER.warning('Attempt to set invalid post sleeping state: %i',
                           state)
            return

        # Set the value
        self._state = state

        # Log the change
        LOGGER.debug('Runtime state changed to %i', self._state)

    def _setup(self):  #pragma: no cover
        """Override to provide any required setup steps."""
        pass

    def _shutdown(self):
        """Override to implement shutdown steps."""
        LOGGER.debug('Shutting down')

        # Wait for the current run to finish
        while self.is_running:
            LOGGER.debug('Waiting for the _process to finish')
            time.sleep(self._SLEEP_UNIT)

        # Change the state to shutting down
        self._set_state(self._STATE_SHUTTING_DOWN)

        # Clear out the timer
        signal.setitimer(signal.ITIMER_PROF, 0, 0)

        # Call a method that may be overwritten to cleanly shutdown
        self._cleanup()

        # Change our state
        self._shutdown_complete()

    def _shutdown_complete(self):
        """Sets the state back to idle when shutdown steps are complete."""
        LOGGER.debug('Shutdown complete')
        self._set_state(self._STATE_IDLE)

    def _sleep(self):
        """Setup the next alarm to fire and then wait for it to fire."""
        LOGGER.debug('Setting up to sleep')

        # Make sure that the application is not shutting down before sleeping
        if self.is_shutting_down:
            LOGGER.debug('Not sleeping, application is trying to shutdown')
            return

        # Set the signal timer
        signal.setitimer(signal.ITIMER_REAL, self._get_wake_interval(), 0)

        # Toggle that we are running
        self._set_state(self._STATE_SLEEPING)

    def _wake(self, _signal, _frame):
        """Fired every time the alarm is signaled. If the app is not shutting
        or shutdown, it will attempt to process.

        :param int _signal: The signal number
        :param frame _frame: The stack frame when received

        """
        LOGGER.debug('Application woke up')

        # Only run the code path if it's not shutting down or shutdown
        if not self.is_shutting_down and not self.is_idle:

            # Note that we're running
            self._set_state(self._STATE_RUNNING)

            # Process actions for the application
            self._process()

            # Wait until we're woken again
            self._sleep()

    def _write_pidfile(self):
        """Write the pidfile out with the process number in the pidfile"""
        with open(_get_pidfile_path(), "w") as handle:
            handle.write(str(os.getpid()))

    @property
    def is_idle(self):
        """Returns True if the controller is idle

        :rtype: bool

        """
        return self._state == self._STATE_IDLE

    @property
    def is_running(self):
        """Returns True if the controller is running

        :rtype: bool

        """
        return self._state == self._STATE_RUNNING

    @property
    def is_shutting_down(self):
        """Returns True if the controller is shutting down

        :rtype: bool

        """
        return self._state == self._STATE_SHUTTING_DOWN

    @property
    def is_sleeping(self):
        """Returns True if the controller is sleeping

        :rtype: bool

        """
        return self._state == self._STATE_SLEEPING

    def run(self):
        """The core method for starting the application. Will setup logging,
        toggle the runtime state flag, block on loop, then call shutdown.

        Redefine this method if you intend to use an IO Loop or some other
        long running process.

        """
        LOGGER.debug('Process running')
        self._setup()
        self._process()
        signal.signal(signal.SIGALRM, self._wake)
        self._sleep()
        while self.is_running or self.is_sleeping:
            signal.pause()


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
    parser.version = "%%prog v%s" % _VERSION
    parser.description = _DESCRIPTION

    # Add default options
    parser.add_option("-c", "--config",
                      action="store",
                      dest="configuration",
                      default=False,
                      help="Path to the configuration file.")

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
    return get_configuration().get(_DAEMON) or dict()


def _get_daemon_context_kargs():
    """Return pre-configured keyword arguments for the DaemonContext

    :rtype: dict

    """
    config = _get_daemon_config()

    # If user is specified in the config, set it for the context
    uid = None
    if config.get('user'):
        uid = _get_uid(config['user'])

    # If group is specified in the config, set it for the context
    gid = None
    if config.get('group'):
        gid = _get_gid(config['group'])

    return {'detach_process': True,
            'gid': gid,
            'pidfile': lockfile.FileLock(path=_get_pidfile_path()),
            'prevent_core': False,
            'signal_map': {signal.SIGHUP: _on_sighup,
                           signal.SIGTERM: _on_sigterm,
                           signal.SIGUSR1: _on_sigusr1,
                           signal.SIGUSR2: _on_sigusr2},
            'uid': uid}


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
    return config.get('pidfile', _PIDFILE) % {'app': _APPNAME}


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
    # Validate the config file exists
    _validate_config_file()

    # Read the config file off the filesystem
    content = _read_config_file()

    # Return the parsed content
    return _parse_yaml(content)


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
    _CONTROLLER._on_sighup()


def _on_sigterm(_signal, _frame):
    """Received when SIGTERM is received.

    :param int _signal: The signal number
    :param frame frame: The stack frame when received

    """
    LOGGER.debug('SIGTERM received, notifying controller')
    _CONTROLLER._on_sigterm()


def _on_sigusr1(_signal, _frame):
    """Received when SIGUSR1 is received.

    :param int _signal: The signal number
    :param frame frame: The stack frame when received

    """
    LOGGER.debug('SIGUSR1 received, notifying controller')
    _CONTROLLER._on_sigusr1()


def _on_sigusr2(_signal, _frame):
    """Received when SIGUSR2 is received.

    :param int _signal: The signal number
    :param frame _frame: The stack frame when received

    """
    LOGGER.debug('SIGUSR2 received, notifying controller')
    _CONTROLLER._on_sigusr2()


def _parse_yaml(content):
    """Parses a YAML string and returns a dictionary object.

    :param str content: The YAML content
    :rtype: dict

    """
    return yaml.load(content)


def _read_config_file():
    """Return the contents of the file specified in _CONFIG_FILE.

    :rtype: str

    """
    with open(_CONFIG_FILE, 'r') as handle:
        return handle.read()


def _remove_debug_only_from_handlers(logging_config):
    """Iterate through each handler removing the invalid dictConfig key of
    debug_only.

    :param dict logging_config: The logging configuration for dictConfig

    """
    for handler in logging_config['handlers']:
        if 'debug_only' in logging_config['handlers'][handler]:
            del logging_config['handlers'][handler]['debug_only']


def _remove_debug_only_handlers(logging_config):
    """Remove any handlers with an attribute of debug_only that is True and
    remove the references to said handlers from any loggers that are referencing
    them.

    :param dict logging_config: The logging configuration for dictConfig

    """
    remove = list()
    for handler in logging_config['handlers']:
        if logging_config['handlers'][handler].get('debug_only'):
            remove.append(handler)

    # Iterate through the handlers to remove and remove them
    for handler in remove:
        del logging_config['handlers'][handler]
        _remove_handler_from_loggers(logging_config['loggers'], handler)


def _remove_handler_from_loggers(loggers, handler):
    """Remove any reference of the specified handler from the loggers in the
    logging_config dictionary.

    :param dict loggers: The loggers section of the logging configuration
    :param str handler: The name of the handler to remove references to

    """
    for LOGGER in loggers:
        try:
            loggers[LOGGER]['handlers'].remove(handler)
        except ValueError:
            pass


def _remove_pidfile():
    """Remove the pidfile from the filesystem"""
    pidfile_path = _get_pidfile_path()
    if os.path.exists(pidfile_path):
        os.unlink(pidfile_path)


def _validate_config_file():
    """Validates the configuration file is set and that it exists.

    :rtype: bool
    :raises: ValueError, OSError

    """
    if not _CONFIG_FILE:
        raise ValueError('Missing internal reference to configuration file')

    if not os.path.exists(_CONFIG_FILE):
        raise OSError('"%s" does not exist' % _CONFIG_FILE)

    return True


def add_config_key(key):
    """Add a top-level key to the expected configuration values for validation

    :param str key: The key to add to the configuration keys

    """
    global _CONFIG_KEYS
    _CONFIG_KEYS.append(key)


def get_logging_config():
    """Return the configuration data for dictConfig

    :rtype: dict

    """
    return get_configuration().get(_LOGGING)


def get_configuration():
    """Return the configuration object, validating that the required top-level
    keys exists.

    :rtype: dict

    """
    # Load the configuration file from disk
    configuration = _load_config()

    # Validate all the top-level items are there
    for key in _CONFIG_KEYS:
        if key not in configuration:
            raise ValueError('Missing required configuration parameter: %s',
                             key)

    # Return the configuration dictionary
    return configuration


def run(controller, option_callback=None):
    """Called by the implementing application to run the application.
    ControllerClass is a class that extends cliapp.Controller.

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
        print 'Error: %s\n' % error
        sys.exit(1)

    # Run the process with the daemon context
    kwargs = _get_daemon_context_kargs()
    if options.foreground:
        kwargs['detach_process'] = False
        kwargs['stderr'] = sys.stderr
        kwargs['stdin'] = sys.stdin
        kwargs['stdout'] = sys.stdout

    # This will be used by the caller to daemonize the application
    try:
        with daemon.DaemonContext(**kwargs):
            LOGGER.debug('Running interactively')
            setup_logging(options.foreground)
            process = controller(options, arguments)
            set_controller(process)
            try:
                process.run()
            except KeyboardInterrupt:
                LOGGER.info('CTRL-C caught, shutting down')
                process._shutdown()
            _remove_pidfile()
    except Exception as error:
        with open('/tmp/clihelper-exception-%s.log' % int(time.time()),
                  'a') as handle:
            handle.write(repr(error))
            traceback.print_exc(25, handle)


def set_appname(appname):
    """Sets the application name for the instance of the application.

    :param str appname: The application name

    """
    global _APPNAME
    _APPNAME = appname


def set_configuration_file(filename):
    """Sets the path for the configuration file.

    :param str filename: The full path to the configuration file
    :raises: ValueError

    """
    global _CONFIG_FILE

    # Make sure the configuration file was specified
    if not filename:
        raise ValueError('Missing required configuration file value')

    # Set the config file to the global variable
    _CONFIG_FILE = filename

    # Validate the file exists
    _validate_config_file()


def set_controller(controller):
    """Sets the controller for the instance of the application.

    :param Controller controller: The Controller object

    """
    global _CONTROLLER
    _CONTROLLER = controller


def set_description(description):
    """Sets the description for the instance of the application.

    :param str description: The app description

    """
    global _DESCRIPTION
    _DESCRIPTION = description


def set_version(version):
    """Sets the version for the instance of the application.

    :param str version: The version #

    """
    global _VERSION
    _VERSION = version


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
    # Get the configuration
    logging_config = get_logging_config()

    # Process debug only handlers
    if not debug:
        _remove_debug_only_handlers(logging_config)

    # Remove any references to debug_only
    _remove_debug_only_from_handlers(logging_config)

    # Run the Dictionary Configuration
    dictConfig(logging_config)
