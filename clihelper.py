"""Command-line application wrapper with configuration and daemonization
support.

"""
__author__ = 'Gavin M. Roy'
__email__ = 'gmr@meetme.com'
__since__ = '2012-04-11'
__version__ = '1.2.0'

import daemon
import grp
import logging
try:
    from logging.config import dictConfig
except ImportError:
    from logutils.dictconfig import dictConfig
import optparse
import os
from daemon import pidfile
import pwd
import signal
import sys
import time
import yaml

_APPNAME = 'clihelper'
_APPLICATION = 'Application'
_DAEMON = 'Daemon'
_LOGGING = 'Logging'
_CONFIG_KEYS = [_APPLICATION, _DAEMON, _LOGGING]
_CONFIG_FILE = None
_CONTROLLER = None
_DESCRIPTION = 'Command Line Daemon'
_PIDFILE = '/var/run/%s.pid'

logger = logging.getLogger(__name__)


class Controller(object):
    """Extend the Controller class with your own application implementing the
    Controller._process method. If you do not want to use sleep based looping
    but rather an IOLoop or some other long-lived blocking loop, redefine
    the Controller._loop method.

    """
    _SLEEP_UNIT = 1
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
        # Default state
        self._set_state(self._STATE_IDLE)

        # Carry these for possible later use
        self._options = options
        self._arguments = arguments

        # Carry debug around for when/if HUP is called or the value is needed
        self._debug = options.foreground

        # Create a new instance of a configuration object
        self._config = get_configuration()

    def _get_application_config(self):
        """Get the configuration data the application itself

        :rtype: dict

        """
        return get_configuration().get(_APPLICATION)

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
        return  self._get_application_config().get('wake_interval',
                                                   self._WAKE_INTERVAL)

    def _loop(self):  #pragma: no cover
        """The process loop, loop until we are running no more."""
        # Loop while we are running
        while self.is_running:

            # Process actions for the application
            self._process()

            # Sleep
            try:
                self._sleep()
            except KeyboardInterrupt:
                self._running = False
                logger.info('CTRL-C received, shutting down')
                break
            except SystemExit:
                self._running = False
                logger.info('Exit signal received, shutting down')
                break

    def _on_sighup(self, _frame):
        """Called when SIGHUP is received, shutdown internal runtime state,
        reloads configuration and then calls Controller.run().

        :param frame _frame: The stack frame when called

        """
        logger.info('Received SIGHUP, restarting internal state')
        self._shutdown()
        self._shutdown_complete()
        self._reload_configuration()
        self.run()

    def _on_sigterm(self, frame):
        """Called when SIGTERM is received, override to implement."""
        logger.info('Received SIGTERM at frame %r', frame)
        self._shutdown()

    def _on_sigusr1(self, _frame):
        """Called when SIGUSR1 is received. Reloads configuration and reruns
        the logger/logging setup.

        :param frame _frame: The stack frame when called

        """
        logger.info('Received SIGUSR1, reloading configuration')
        self._reload_configuration()

    def _on_sigusr2(self, frame):  #pragma: no cover
        """Called when SIGUSR2 is received, override to implement."""
        logger.info('Received SIGUSR2 at frame %r', frame)

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
        _setup_logging(self._debug)

    def _set_state(self, state):
        """Set the runtime state of the Controller.

        :param int state: The runtime state
        :raises: ValueError

        """
        if state not in [self._STATE_IDLE,
                         self._STATE_RUNNING,
                         self._STATE_SLEEPING,
                         self._STATE_SHUTTING_DOWN]:
            raise ValueError('Invalid Runtime State')

        # Set the value
        self._state = state

        # Log the change
        logger.debug('Runtime state changed to %i', self._state)

    def _setup(self):  #pragma: no cover
        """Override to provide any required setup steps."""
        pass

    def _shutdown(self):
        """Override to implement shutdown steps."""
        logger.debug('Shutting down')
        self._set_state(self._STATE_SHUTTING_DOWN)

    def _shutdown_complete(self):
        """Sets the state back to idle when shutdown steps are complete."""
        logger.debug('Shutdown complete')
        self._set_state(self._STATE_IDLE)

    def _sleep(self):
        """Sleep for the configured sleep interval or until the app has been
        told to shutdown.

        """
        # Calculate when the application should wake
        wake_time = self._wake_time()

        # Set the state to sleeping
        self._set_state(self._STATE_SLEEPING)

        # While we've not exceeded the end_time and we're still running
        while wake_time > time.time() and self.is_running:
            time.sleep(self._SLEEP_UNIT)

        # Set the state back to running
        logger.debug('Waking')
        self._set_state(self._STATE_RUNNING)

    def _wake_time(self):
        """Calculate the wakeup time for sleeping

        :rtype: int

        """
        wake_interval =  self._get_wake_interval()
        end_time = int(time.time() + wake_interval)
        logger.debug('Sleeping %i seconds, waking at %.2f',
                           wake_interval, end_time)
        return end_time

    @property
    def is_running(self):
        """Returns True if the controller is running

        :rtype: bool

        """
        return self._state in [self._STATE_RUNNING, self._STATE_SLEEPING]

    @property
    def is_shutting_down(self):
        """Returns True if the controller is shutting down

        :rtype: bool

        """
        return self._state == self._STATE_SHUTTING_DOWN

    def run(self):
        """The core method for starting the application. Will setup logging,
        toggle the runtime state flag, block on loop, then call shutdown.

        """
        # Call this now because the app may be in a new process
        logger.info('Process running')

        # Call the _setup method
        self._setup()

        # Toggle that we are running
        self._set_state(self._STATE_RUNNING)

        # Loop until we're not
        self._loop()

        # Wait until shutdown is complete
        while self.is_shutting_down:
            self._sleep()

        # Signal that shutdown is complete
        self._shutdown_complete()


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
    return get_configuration().get(_DAEMON)


def _get_daemon_context():
    """Return an instance of the daemon.DaemonContext class.

    :rtype: daemon.DaemonContext

    """
    # Return the daemon configuration values
    config = _get_daemon_config()

    # Create the new context to daemonize with
    context = _new_daemon_context()

    # If user is specified in the config, set it for the context
    if config.get('user'):
        context.uid = _get_uid(config['user'])

    # If group is specified in the config, set it for the context
    if config.get('group'):
        context.gid = _get_gid(config['group'])

    # Set the pidfile to write when app has started
    context.pidfile = pidfile.PIDLockFile(config.get('pidfile', _PIDFILE))

    # Setup the signal map
    context.signal_map = {signal.SIGHUP: _on_sighup,
                          signal.SIGTERM: _on_sigterm,
                          signal.SIGUSR1: _on_sigusr1,
                          signal.SIGUSR2: _on_sigusr2}

    # This will be used by the caller to daemonize the application
    return context


def _get_gid(group):
    """Return the group id for the specified group.

    :param str group: The group name to get the id for
    :rtype: int

    """
    return grp.getgrnam(group).gr_gid


def _get_logging_config():
    """Return the configuration data for dictConfig

    :rtype: dict

    """
    return get_configuration().get(_LOGGING)


def _get_pidfile_path():
    """Return the pidfile path for the daemon context.

    :rtype: str

    """
    config = _get_daemon_config()
    return config.get('pidfile', _PIDFILE % _APPNAME)


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


def _new_daemon_context():
    """Return a new daemon context.

    :rtype: daemon.DaemonContext

    """
    return daemon.DaemonContext()


def _new_option_parser():
    """Return a new optparse.OptionParser instance.

    :rtype: optparse.OptionParser

    """
    return optparse.OptionParser()


def _on_sighup(_signal, frame):
    """Received when SIGHUP is received.

    :param int _signal: The signal number
    :param frame frame: The stack frame when received

    """
    _CONTROLLER._on_sighup(frame)


def _on_sigterm(_signal, frame):
    """Received when SIGTERM is received.

    :param int _signal: The signal number
    :param frame frame: The stack frame when received

    """
    _CONTROLLER._on_sigterm(frame)


def _on_sigusr1(_signal, frame):
    """Received when SIGUSR1 is received.

    :param int _signal: The signal number
    :param frame frame: The stack frame when received

    """
    _CONTROLLER._on_sigusr1(frame)


def _on_sigusr2(_signal, frame):
    """Received when SIGUSR1 is received.

    :param int _signal: The signal number
    :param frame frame: The stack frame when received

    """
    _CONTROLLER._on_sigusr2(frame)


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
    for logger in loggers:
        try:
            loggers[logger]['handlers'].remove(handler)
        except ValueError:
            pass


def _setup_logging(debug):
    """Setup the logging configuration and assign the logger. If debug is False
    strip any handlers and their references from the configuration.

    :param bool debug: The app is in debug mode

    """
    # Get the configuration
    logging_config = _get_logging_config()

    # Process debug only handlers
    if not debug:
        _remove_debug_only_handlers(logging_config)

    # Remove any references to debug_only
    _remove_debug_only_from_handlers(logging_config)

    # Run the Dictionary Configuration
    dictConfig(logging_config)


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

    :param str key: The key to add to the configuraiton keys

    """
    global _CONFIG_KEYS
    _CONFIG_KEYS.append(key)

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

    if options.foreground:
        _setup_logging(True)
        process = controller(options, arguments)
        set_controller(process)
        try:
            return process.run()
        except KeyboardInterrupt:
            logging.info('CTRL-C caught, shutting down')
            process._on_sigterm(None)
            logging.info('Shutdown')
            return

    # Run the process with the daemon context
    with _get_daemon_context():
        _setup_logging(False)
        process = controller(options, arguments)
        set_controller(process)
        process.run()


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
