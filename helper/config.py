"""
Responsible for reading in configuration files, validating the proper
format and providing sane defaults for parts that don't have any.

"""
import json
import logging
import logging.config
import os
from os import path
import sys
try:
    from urllib import parse
except ImportError:  # Python 2.7 support
    import urlparse as parse

import flatdict
import yaml

LOGGER = logging.getLogger(__name__)

APPLICATION = {'wake_interval': 60}

DAEMON = {'user': None,
          'group': None,
          'pidfile': None,
          'prevent_core': True}

LOGGING_FORMAT = ('%(levelname) -10s %(asctime)s %(process)-6d '
                  '%(processName) -20s %(threadName)-12s %(name) -30s '
                  '%(funcName) -25s L%(lineno)-6d: %(message)s')

LOGGING = {
    'disable_existing_loggers': True,
    'filters': {},
    'formatters': {
        'verbose': {
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'format': LOGGING_FORMAT
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'root': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': logging.CRITICAL
        }
    },
    'incremental': False,
    'loggers': {},
    'root': {
        'handlers': ['root']
    },
    'version': 1}


class Config(object):
    """The Config object holds the current state of the configuration for an
    application. If no configuration file is provided, it will used a set of
    defaults with very basic behavior for logging and daemonization.

    """
    def __init__(self, file_path=None):
        """Create a new instance of the configuration object, passing in the
        path to the configuration file.

        :param str file_path: The path to the configuration file
        :raises: ValueError

        """
        self._values = self._default_configuration()
        self._file_path = self._normalize_file_path(file_path)
        if self._file_path:
            self._values.update(self._load_config_file())

    def get(self, name, default=None):
        """Return the value for key if key is in the configuration, else default.

        :param str name: The key name to return
        :param mixed default: The default value for the key
        :return: mixed

        """
        return self._values.get(name, default)

    @property
    def application(self):
        return self._values['Application'].as_dict()

    @property
    def daemon(self):
        return self._values['Daemon'].as_dict()

    @property
    def logging(self):
        return self._values['Logging'].as_dict()

    def reload(self):
        """Reload the configuration from disk returning True if the
        configuration has changed from the previous values.

        """
        config = self._default_configuration()
        if self._file_path:
            config.update(self._load_config_file())
        if config != self._values:
            self._values = config
            return True
        return False

    @staticmethod
    def _default_configuration():
        """Return the default configuration for Helper

        :rtype: dict

        """
        return flatdict.FlatDict({
            'Application': APPLICATION,
            'Daemon': DAEMON,
            'Logging': LOGGING
        })

    def _load_config_file(self):
        """Load the configuration file into memory, returning the content.

        """
        LOGGER.info('Loading configuration from %s', self._file_path)
        if self._file_path.endswith('json'):
            config = self._load_json_config()
        else:
            config = self._load_yaml_config()
        for key, value in [(k, v) for k, v in config.items()]:
            if key.title() != key:
                config[key.title()] = value
                del config[key]
        return flatdict.FlatDict(config)

    def _load_json_config(self):
        """Load the configuration file in JSON format

        :rtype: dict

        """
        try:
            return json.loads(self._read_config())
        except ValueError as error:
            raise ValueError(
                'Could not read configuration file: {}'.format(error))

    def _load_yaml_config(self):
        """Loads the configuration file from a .yaml or .yml file

        :type: dict

        """
        try:
            config = self._read_config()
        except OSError as error:
            raise ValueError('Could not read configuration file: %s' % error)
        try:
            return yaml.safe_load(config)
        except yaml.YAMLError as error:
            message = '\n'.join(['    > %s' % line
                                 for line in str(error).split('\n')])
            sys.stderr.write('\n\n  Error in the configuration file:\n\n'
                             '{}\n\n'.format(message))
            sys.stderr.write('  Configuration should be a valid YAML file.\n')
            sys.stderr.write('  YAML format validation available at '
                             'http://yamllint.com\n')
            raise ValueError(error)

    @staticmethod
    def _normalize_file_path(file_path):
        """Normalize the file path value.

        :param str file_path: The file path as passed in
        :rtype: str

        """
        if not file_path:
            return None
        elif file_path.startswith('s3://') or \
                file_path.startswith('http://') or \
                file_path.startswith('https://'):
            return file_path
        return path.abspath(file_path)

    def _read_config(self):
        """Read the configuration from the various places it may be read from.

        :rtype: str
        :raises: ValueError

        """
        if not self._file_path:
            return None
        elif self._file_path.startswith('s3://'):
            return self._read_s3_config()
        elif self._file_path.startswith('http://') or \
                self._file_path.startswith('https://'):
            return self._read_remote_config()
        elif not path.exists(self._file_path):
            raise ValueError(
                'Configuration file not found: {}'.format(self._file_path))

        with open(self._file_path, 'r') as handle:
            return handle.read()

    def _read_remote_config(self):
        """Read a remote config via URL.

        :rtype: str
        :raises: ValueError

        """
        try:
            import requests
        except ImportError:
            requests = None
        if not requests:
            raise ValueError(
                'Remote config URL specified but requests not installed')
        result = requests.get(self._file_path)
        if not result.ok:
            raise ValueError(
                'Failed to retrieve remote config: {}'.format(
                    result.status_code))
        return result.text

    def _read_s3_config(self):
        """Read in the value of the configuration file in Amazon S3.

        :rtype: str
        :raises: ValueError

        """
        try:
            import boto3
            import botocore.exceptions
        except ImportError:
            boto3, botocore = None, None

        if not boto3:
            raise ValueError(
                's3 URL specified for configuration but boto3 not installed')
        parsed = parse.urlparse(self._file_path)
        try:
            response = boto3.client(
                's3', endpoint_url=os.environ.get('S3_ENDPOINT')).get_object(
                    Bucket=parsed.netloc, Key=parsed.path.lstrip('/'))
        except botocore.exceptions.ClientError as e:
            raise ValueError(
                'Failed to download configuration from S3: {}'.format(e))
        return response['Body'].read().decode('utf-8')


class LoggingConfig(object):
    """The Logging class is used for abstracting away dictConfig logging
    semantics and can be used by sub-processes to ensure consistent logging
    rule application.

    """
    DEBUG_ONLY = 'debug_only'
    HANDLERS = 'handlers'
    LOGGERS = 'loggers'

    def __init__(self, configuration, debug=None):
        """Create a new instance of the Logging object passing in the
        DictConfig syntax logging configuration and a debug flag.

        :param dict configuration: The logging configuration
        :param bool debug: Toggles use of debug_only loggers

        """
        # Force a NullLogger for some libraries that require it
        root_logger = logging.getLogger()
        root_logger.addHandler(logging.NullHandler())

        self.config = dict(configuration)
        self.debug = debug
        self.configure()

    def update(self, configuration, debug=None):
        """Update the internal configuration values, removing debug_only
        handlers if debug is False. Returns True if the configuration has
        changed from previous configuration values.

        :param dict configuration: The logging configuration
        :param bool debug: Toggles use of debug_only loggers
        :rtype: bool

        """
        if self.config != dict(configuration) and debug != self.debug:
            self.config = dict(configuration)
            self.debug = debug
            self.configure()
            return True
        return False

    def configure(self):
        """Configure the Python stdlib logger"""
        if self.debug is not None and not self.debug:
            self._remove_debug_handlers()
        self._remove_debug_only()
        logging.config.dictConfig(self.config)
        try:
            logging.captureWarnings(True)
        except AttributeError:
            pass

    def _remove_debug_handlers(self):
        """Remove any handlers with an attribute of debug_only that is True and
        remove the references to said handlers from any loggers that are
        referencing them.

        """
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
        self._remove_debug_only()

    def _remove_debug_only(self):
        """Iterate through each handler removing the invalid dictConfig key of
        debug_only.

        """
        LOGGER.debug('Removing debug only from handlers')
        for handler in self.config[self.HANDLERS]:
            if self.DEBUG_ONLY in self.config[self.HANDLERS][handler]:
                del self.config[self.HANDLERS][handler][self.DEBUG_ONLY]
