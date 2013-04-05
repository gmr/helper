"""
Tests for the clihelper module

"""
__author__ = 'Gavin M. Roy'
__email__ = 'gmr@meetme.com'
__since__ = '2012-04-18'

import copy
import daemon
try:
    from logging.config import dictConfig
except ImportError:
    from logutils.dictconfig import dictConfig
import grp
import mock
import logging
import optparse
import os
import signal
import sys
import time
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import yaml

sys.path.insert(0, '..')
import clihelper

_WAKE_INTERVAL = 5
_APPNAME = 'Test'
_LOGGER_CONFIG = {_APPNAME: {'level': 'ERROR'}}
_CONFIG = {clihelper._APPLICATION: {'wake_interval': _WAKE_INTERVAL},
           clihelper._DAEMON: {'user': 'root',
                               'group': 'wheel',
                               'pidfile': '/tmp/test.pid'},
           clihelper._LOGGING: {'version': 1,
                                'formatters': [],
                                'filters': [],
                                'handlers': [],
                                'loggers': _LOGGER_CONFIG}}


class BaseTests(unittest.TestCase):

    def _setup_mock_load_config(self):
        self._mock_load_config = mock.Mock(return_value=_CONFIG)
        self._load_config_patcher = mock.patch('clihelper._load_config',
                                               self._mock_load_config)
        self._load_config_patcher.start()
        self.addCleanup(self._load_config_patcher.stop)

    def _return_context(self):
        return self._daemon_context

    def _return_optparse(self):
        return self._optparse

    def _setup_mock_daemon_context(self):
        self._daemon_context = mock.Mock(spec=daemon.DaemonContext)

    def _setup_mock_new_option_parser(self):
        self._optparse = mock.Mock(spec=optparse.OptionParser)
        self._optparse.parse_args = mock.Mock(return_value=(self._options, []))
        self._optparse_patcher = mock.patch('clihelper._new_option_parser',
                                            self._return_optparse)
        self._optparse_patcher.start()
        self.addCleanup(self._optparse_patcher.stop)

    def _mock_options(self):
        mock_options = mock.Mock(spec=optparse.Values)
        mock_options.foreground = True
        mock_options.configuration = '/dev/null'
        return mock_options

    def setUp(self):
        clihelper.set_configuration_file('/dev/null')
        self._options = self._mock_options()
        self._setup_mock_load_config()
        self._setup()
        self._controller = clihelper.Controller(self._options, list())
        clihelper.set_controller(self._controller)

    def tearDown(self):
        clihelper._CONFIG_FILE = None
        del self._controller

    def _setup(self):
        pass


class CLIHelperTests(BaseTests):

    def _setup(self):
        self._setup_mock_daemon_context()
        self._setup_mock_new_option_parser()

    def test_cli_options(self):
        clihelper.setup('Foo', 'Bar', '1.0')
        options, arguments = clihelper._cli_options(None)
        self.assertIsInstance(options, optparse.Values)

    def test_cli_options_with_callback(self):
        callback = mock.Mock()
        clihelper.setup('Foo', 'Bar', '1.0')
        clihelper._cli_options(callback)
        self.assertTrue(callback.called)

    def test_get_configuration(self):
        self.assertEqual(clihelper.get_configuration(), _CONFIG)

    def test_get_configuration_invalid_config(self):
        _BAD_CONFIG = copy.deepcopy(_CONFIG)
        del _BAD_CONFIG[clihelper._LOGGING]
        self._mock_load_config.return_value = _BAD_CONFIG
        self.assertRaises(ValueError, clihelper.get_configuration)
        self._mock_load_config.return_value = _CONFIG

    def test_run_invalid_config(self):
        options = self._mock_options()
        options.configuration = ''
        config = {'return_value': (options, list())}
        with mock.patch('clihelper._cli_options', **config):
            with mock.patch('sys.exit'):
                self.assertRaises(ValueError,
                                  clihelper.run(TestPassthruController))

    def test_get_daemon_config(self):
        self.assertEqual(clihelper._get_daemon_config(),
                         _CONFIG[clihelper._DAEMON])

    def test_get_logging_config(self):
        self.assertEqual(clihelper.get_logging_config(),
                         _CONFIG[clihelper._LOGGING])

    def test_get_gid(self):
        value = 'wheel'
        self.assertEqual(clihelper._get_gid(value), grp.getgrnam(value).gr_gid)

    def test_get_pidfile_path(self):
        self.assertEqual(clihelper._get_pidfile_path(),
                         _CONFIG[clihelper._DAEMON]['pidfile'])

    def test_get_uid(self):
        self.assertEqual(clihelper._get_uid('root'), 0)

    def test_on_sighup(self):
        frame = time.time()
        with mock.patch.object(self._controller, '_on_sighup') as sighup:
            clihelper._on_sighup(signal.SIGHUP, frame)
            self.assertTrue(sighup.called)

    def test_on_sigterm(self):
        frame = time.time()
        with mock.patch.object(self._controller, '_on_sigterm') as sigterm:
            clihelper._on_sigterm(signal.SIGTERM, frame)
            self.assertTrue(sigterm.called)

    def test_on_sigusr1(self):
        frame = time.time()
        with mock.patch.object(self._controller, '_on_sigusr1') as sigusr1:
            clihelper._on_sigusr1(signal.SIGUSR1, frame)
            self.assertTrue(sigusr1.called)

    def test_on_sigusr2(self):
        frame = time.time()
        with mock.patch.object(self._controller, '_on_sigusr2') as sigusr2:
            clihelper._on_sigusr2(signal.SIGUSR2, frame)
            self.assertTrue(sigusr2.called)

    def test_parse_yaml(self):
        content = yaml.dump(_CONFIG)
        result = clihelper._parse_yaml(content)
        self.assertEqual(result, _CONFIG)

    def test_read_config_file(self):
        filename = '/tmp/clihelper.test.%.2f' % time.time()
        content = yaml.dump(_CONFIG)
        with open(filename, 'w') as handle:
            handle.write(content)
        clihelper.set_configuration_file(filename)
        result = clihelper._read_config_file()
        os.unlink(filename)
        self.assertEqual(result, content)

    def test_set_appname(self):
        clihelper.set_appname(__name__)
        self.assertEqual(clihelper._APPNAME, __name__)

    def test_set_configuration_file(self):
        filename = '/dev/null'
        clihelper.set_configuration_file(filename)
        self.assertEqual(clihelper._CONFIG_FILE, filename)

    def test_set_empty_configuration_file(self):
        self.assertRaises(ValueError, clihelper.set_configuration_file, None)

    def test_set_controller(self):
        self.assertEqual(clihelper._CONTROLLER, self._controller)

    def test_set_description(self):
        clihelper.set_description(self.__class__.__name__)
        self.assertEqual(clihelper._DESCRIPTION, self.__class__.__name__)

    def test_set_version(self):
        clihelper.set_version(__since__)
        self.assertEqual(clihelper._VERSION, __since__)

    def test_setup_appname(self):
        value = 'TestAppName:%.2f' % time.time()
        clihelper.setup(value, None, None)
        self.assertEqual(clihelper._APPNAME, value)

    def test_setup_description(self):
        value = 'TestDescription:%.2f' % time.time()
        clihelper.setup(None, value, None)
        self.assertEqual(clihelper._DESCRIPTION, value)

    def test_setup_logging(self):
        clihelper.setup_logging(True)
        logger = logging.getLogger(_APPNAME)
        level_name = _LOGGER_CONFIG[_APPNAME]['level']
        level = logging.getLevelName(level_name)
        self.assertEqual(logger.level, level)

    def test_setup_version(self):
        value = 'TestVersion:%.2f' % time.time()
        clihelper.setup(None, None, value)
        self.assertEqual(clihelper._VERSION, value)
        clihelper._CONFIG_FILE = '/dev/null'

    def test_validate_config_file(self):
        clihelper._CONFIG_FILE = '/tmp/clihelper-test-%.2f' % time.time()
        with open(clihelper._CONFIG_FILE, 'w') as handle:
            handle.write('Foo\n')
        response = clihelper._validate_config_file()
        os.unlink(clihelper._CONFIG_FILE)
        clihelper._CONFIG_FILE = '/dev/null'
        self.assertTrue(response)

    def test_validate_config_file_not_empty(self):
        clihelper._CONFIG_FILE = None
        self.assertRaises(ValueError, clihelper._validate_config_file)
        clihelper._CONFIG_FILE = '/dev/null'

    def test_validate_config_file_does_not_exist(self):
        clihelper._CONFIG_FILE = '/tmp/clihelper-test-%.2f' % time.time()
        self.assertRaises(OSError, clihelper._validate_config_file)

    def _logging_config_remove_debug_only_values(self):
        config = {'handlers':
                          {'debug_true':
                               {'class': 'logging.StreamHandler',
                               'debug_only': True},
                           'debug_false':
                               {'class': 'logging.FileHandler',
                                'debug_only': False}},
                  'loggers': {'Test': {'handlers': ['debug_true',
                                                    'debug_false']},
                              'Foo': {'handlers': ['debug_false']}}}

        expectation = {'handlers':
                           {'debug_false':
                               {'class': 'logging.FileHandler',
                                'debug_only': False}},
                       'loggers': {'Test': {'handlers': ['debug_false']},
                                   'Foo': {'handlers': ['debug_false']}}}
        return config, expectation

    def test_remove_handler_from_loggers(self):
        config, expectation = self._logging_config_remove_debug_only_values()
        clihelper._remove_handler_from_loggers(config['loggers'], 'debug_true')
        self.assertEqual(config['loggers'], expectation['loggers'])

    def test_remove_debug_only_handlers(self):
        config, expectation = self._logging_config_remove_debug_only_values()
        clihelper._remove_debug_only_handlers(config)
        self.assertEqual(config, expectation)

    def test_remove_debug_only_from_handlers(self):
        config, expectation = self._logging_config_remove_debug_only_values()
        clihelper._remove_debug_only_from_handlers(config)
        for handler in config['handlers']:
            self.assertFalse('debug_only' in config['handlers'][handler])

    def test_add_config_key(self):
        test_option = 'Test'
        clihelper.add_config_key(test_option)
        self.assertTrue(test_option in clihelper._CONFIG_KEYS)
        clihelper._CONFIG_KEYS.remove(test_option)


class TestController(clihelper.Controller):

    def __init__(self, options, arguments):
        super(TestController, self).__init__(options, arguments)
        self.shutdown_completed = False
        self.slept = False
        self._config[clihelper._APPLICATION]['wake_interval'] = 0

    def _shutdown_complete(self):
        super(TestController, self)._shutdown_complete()
        self.shutdown_completed = True

    def _process(self):
        pass

    def _loop(self):
        self._process()
        self._sleep()
        self._shutdown()

    def _set_state(self, state):
        if state == self._STATE_SLEEPING:
            self.slept = True
        self._state = state


class TestPassthruController(TestController):

    def __init__(self, options, arguments):
        super(TestPassthruController, self).__init__(options, arguments)
        self._config[clihelper._APPLICATION]['wake_interval'] = 1
        self.process_called = False
        self.run_called = False
        self.setup_called = False
        self.sleep_called = False

    def _run(self):
        logging.getLogger('Test').debug('In %r._run', self)
        self.run_called = True

    def _process(self):
        logging.getLogger('Test').debug('In %r._process', self)
        self.process_called = True

    def _sleep(self):
        logging.getLogger('Test').debug('In %r._sleep', self)
        self.sleep_called = True

    def _setup(self):
        logging.getLogger('Test').debug('In %r._setup', self)
        self.setup_called = True


class ControllerTests(BaseTests):

    def _setup(self):
        self._setup_mock_daemon_context()
        self._setup_mock_new_option_parser()

    def test_new_instance_has_idle_state(self):
        self.assertEqual(self._controller._state,
                         clihelper.Controller._STATE_IDLE)

    def test_new_instance_is_idle(self):
        self.assertTrue(self._controller.is_idle)

    def test_new_instance_is_not_running(self):
        self.assertFalse(self._controller.is_running)

    def test_new_instance_is_not_shutting_down(self):
        self.assertFalse(self._controller.is_shutting_down)

    def test_set_state_invalid_option(self):
        self.assertRaises(ValueError, self._controller._set_state, -1)

    def test_set_state_invalid_state_when_running(self):
        self._controller._state = self._controller._STATE_RUNNING
        self._controller._set_state(self._controller._STATE_IDLE)
        self.assertEqual(self._controller._state,
                         self._controller._STATE_RUNNING)

    def test_set_state_invalid_state_when_shutting_down(self):
        self._controller._state = self._controller._STATE_SHUTTING_DOWN
        self._controller._set_state(self._controller._STATE_RUNNING)
        self.assertEqual(self._controller._state,
                         self._controller._STATE_SHUTTING_DOWN)

    def test_set_state_invalid_state_when_sleeping(self):
        self._controller._state = self._controller._STATE_SLEEPING
        self._controller._set_state(self._controller._STATE_IDLE)
        self.assertEqual(self._controller._state,
                         self._controller._STATE_SLEEPING)

    def test_sleep_bails_when_shutting_down(self):
        self._controller._state = self._controller._STATE_SHUTTING_DOWN
        with mock.patch('signal.setitimer') as mfunction:
            try:
                self._controller._sleep()
                self.assertFalse(mfunction.called)
            except AssertionError:
                self.assertTrue(False, 'Did not cleanly exit')

    def test_sleep_calls_itimer(self):
        self._controller._state = self._controller._STATE_RUNNING
        with mock.patch('signal.pause') as _pause:
            with mock.patch('signal.setitimer') as setitimer:
                self._controller._sleep()
                self.assertTrue(setitimer.called)

    def test_sleep_sets_right_state(self):
        self._controller._state = self._controller._STATE_RUNNING
        with mock.patch('signal.pause') as _pause:
            with mock.patch('signal.setitimer') as _setitimer:
                self._controller._sleep()
                self.assertEqual(self._controller._state,
                                 self._controller._STATE_SLEEPING)

    def test_sleep_calls_pause(self):
        self._controller._state = self._controller._STATE_RUNNING
        with mock.patch('signal.pause') as pause:
            with mock.patch('signal.setitimer') as _setitimer:
                self._controller._sleep()
                pause.assert_called_once()

    def test_get_application_config(self):
        self.assertEqual(self._controller._get_application_config(),
                         _CONFIG[clihelper._APPLICATION])

    def test_get_config_return_value(self):
        key = 'wake_interval'
        self.assertEqual(self._controller._get_config(key),
                         _CONFIG[clihelper._APPLICATION][key])

    def test_get_config_calls_get_configuration(self):
        with mock.patch('clihelper.get_configuration') as mock_function:
            mock_function.return_value = _CONFIG
            self._controller._get_config('wake_interval')
            mock_function.assert_called_once()

    def test_get_wake_interval(self):
        self.assertEqual(self._controller._get_wake_interval(),
                         _CONFIG[clihelper._APPLICATION]['wake_interval'])

    def test_process_not_implemented(self):
        self.assertRaises(NotImplementedError, self._controller._process)

    def test_on_sigusr1(self):
        self.assertEqual(self._controller._config, _CONFIG)
        _NEW_CONFIG = copy.deepcopy(_CONFIG)
        _NEW_CONFIG['test_value'] = time.time()
        self._mock_load_config.return_value = _NEW_CONFIG
        self._controller._state = self._controller._STATE_RUNNING
        self._controller._on_sigusr1()
        self.assertEqual(self._controller._config, _NEW_CONFIG)
        self._mock_load_config.return_value = _CONFIG

    def test_reload_configuration(self):
        self.assertEqual(self._controller._config, _CONFIG)
        _NEW_CONFIG = copy.deepcopy(_CONFIG)
        _NEW_CONFIG['test_value'] = time.time()
        self._mock_load_config.return_value = _NEW_CONFIG
        self._controller._reload_configuration()
        self.assertEqual(self._controller._config, _NEW_CONFIG)
        self._mock_load_config.return_value = _CONFIG

    def test_shutdown_complete(self):
        self._controller._state = self._controller._STATE_SHUTTING_DOWN
        self._controller._shutdown_complete()
        self.assertEqual(self._controller._state, self._controller._STATE_IDLE)

    def test_shutdown_clears_itimer(self):
        self._controller._state = self._controller._STATE_SLEEPING
        with mock.patch('signal.setitimer') as setitimer:
            self._controller._shutdown()
            setitimer.assert_called_with(signal.ITIMER_PROF, 0, 0)

    def test_shutdown_calls_time_sleep(self):
        slept = False
        def sleep_now(value):
            logging.debug('Value: %r', value)
            self._controller._state = self._controller._STATE_SLEEPING
        self._controller._state = self._controller._STATE_RUNNING
        with mock.patch('signal.setitimer') as _setitimer:
            with mock.patch('time.sleep', side_effect=sleep_now) as time_sleep:
                self._controller._shutdown()
                time_sleep.assert_called_with(self._controller._SLEEP_UNIT)

    def test_shutdown_calls_shutdown_complete(self):
        self._controller._state = self._controller._STATE_SLEEPING
        with mock.patch('signal.setitimer') as _setitimer:
            self._controller._shutdown()
        self.assertEqual(self._controller._state, self._controller._STATE_IDLE)

    def test_on_hup_calls_reload(self):
        self.reloaded = False
        self.run_called = False
        self.shutdown_called = False
        def reload_configuration():
            self.reloaded = True
        def run():
            self.run_called = True
        def _shutdown():
            self.shutdown_called = True
        self._controller._reload_configuration = reload_configuration
        self._controller._shutdown = _shutdown
        self._controller.run = run
        self._controller._on_sighup()
        self.assertTrue(self.reloaded)

    def test_on_hup_calls_run(self):
        self.reloaded = False
        self.run_called = False
        self.shutdown_called = False
        def reload_configuration():
            self.reloaded = True
        def run():
            self.run_called = True
        def _shutdown():
            self.shutdown_called = True
        self._controller._reload_configuration = reload_configuration
        self._controller._shutdown = _shutdown
        self._controller.run = run
        self._controller._on_sighup()
        self.assertTrue(self.run_called)

    def test_on_hup_calls_shutdown(self):
        self.reloaded = False
        self.run_called = False
        self.shutdown_called = False
        def reload_configuration():
            self.reloaded = True
        def run():
            self.run_called = True
        def _shutdown():
            self.shutdown_called = True
        self._controller._reload_configuration = reload_configuration
        self._controller._shutdown = _shutdown
        self._controller.run = run
        self._controller._on_sighup()
        self.assertTrue(self.shutdown_called)

    def test_on_sigusr1_calls_reload_configuration(self):
        self._controller._state = self._controller._STATE_SLEEPING
        self.reloaded = False
        def reload_configuration():
            self.reloaded = True
        self._controller._reload_configuration = reload_configuration
        with mock.patch('signal.pause') as _pause:
            self._controller._on_sigusr1()
            self.assertTrue(self.reloaded)

    def test_on_sigusr1_calls_signal_pause(self):
        self._controller._state = self._controller._STATE_SLEEPING
        self.reloaded = False
        def reload_configuration():
            self.reloaded = True
        self._controller._reload_configuration = reload_configuration
        with mock.patch('signal.pause') as pause:
            self._controller._on_sigusr1()
            self.assertTrue(pause.called)

    def test_on_sigusr2_calls_signal_pause(self):
        self._controller._state = self._controller._STATE_SLEEPING
        with mock.patch('signal.pause') as pause:
            self._controller._on_sigusr2()
            self.assertTrue(pause.called)
