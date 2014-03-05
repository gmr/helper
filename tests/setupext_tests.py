try:
    import unittest2 as unittest
except ImportError:
    import unittest

import mock

import helper.setupext


class PatchedTestMixin(object):

    def setUp(self):
        super(PatchedTestMixin, self).setUp()
        self._patches = []

    def tearDown(self):
        for patcher in self._patches:
            patcher.stop()
        self._patches = []
        super(PatchedTestMixin, self).tearDown()

    def add_patch(self, name, **kwargs):
        self._patches.append(mock.patch('helper.setupext.' + name, **kwargs))
        return self._patches[-1].start()


class RunCommandTests(PatchedTestMixin, unittest.TestCase):

    def assertHasAttribute(self, obj, attribute):
        if getattr(obj, attribute, mock.sentinel.default) \
                is mock.sentinel.default:
            self.fail('Expected {0} to have attribute named {1}'.format(
                obj, attribute))

    def setUp(self):
        super(RunCommandTests, self).setUp()
        self.add_patch('Command.__init__', return_value=None)
        self.command = helper.setupext.RunCommand(mock.Mock())

    def test_description(self):
        self.assertHasAttribute(helper.setupext.RunCommand, 'description')

    def test_user_options(self):
        self.assertEquals(helper.setupext.RunCommand.user_options[0],
                          ('configuration=', 'c', mock.ANY))
        self.assertEquals(helper.setupext.RunCommand.user_options[1],
                          ('controller=', 'C', mock.ANY))

    def test_initialize_options(self):
        self.command.initialize_options()
        self.assertIsNone(getattr(self.command, 'controller'))
        self.assertIsNone(getattr(self.command, 'configuration'))

    def test_finalize_options(self):
        finalize_options = self.add_patch('Command.finalize_options')

        self.command.finalize_options()
        self.assertFalse(finalize_options.called)



class RunCommandRunTests(PatchedTestMixin, unittest.TestCase):

    def setUp(self):
        super(RunCommandRunTests, self).setUp()
        self.controller_module = mock.Mock()
        self.command_class = mock.Mock()
        # `start` runs until Ctrl+C is pressed, mimic that
        self.command_class.return_value.start.side_effect = KeyboardInterrupt

        self.add_patch('Command.__init__', return_value=None)
        self.import_stmt = self.add_patch('__import__', create=True)
        self.getattr_stmt = self.add_patch('getattr', create=True)
        self.getattr_stmt.side_effect = [self.controller_module,
                                         self.command_class]
        self.platform = self.add_patch('platform')
        self.parser = self.add_patch('parser')

        self.command = helper.setupext.RunCommand(mock.Mock())
        self.command.controller = 'package.controller.command'
        self.command.configuration = None

        self.command.run()

    def test_controller_is_imported(self):
        self.import_stmt.assert_called_once_with('package.controller')
        self.getattr_stmt.assert_any_call(self.import_stmt.return_value,
                                          'controller')
        self.getattr_stmt.assert_any_call(self.controller_module, 'command')

    def test_parser_is_fetched_from_config(self):
        self.parser.get.assert_called_once_with()

    def test_command_line_is_parsed(self):
        parser = self.parser.get.return_value
        parser.parse_args.assert_called_once_with(['-f'])

    def test_controller_is_created(self):
        self.command_class.assert_called_once_with(
            self.parser.get.return_value.parse_args.return_value,
            self.platform,
        )

    def test_should_start_controller(self):
        self.command_class.return_value.start.assert_called_once_with()

    def test_should_stop_controller(self):
        self.command_class.return_value.stop.assert_called_once_with()


class RunCommandParameterTests(PatchedTestMixin, unittest.TestCase):

    def setUp(self):
        super(RunCommandParameterTests, self).setUp()
        self.add_patch('Command.__init__', return_value=None)
        self.add_patch('__import__', create=True)
        self.add_patch('getattr', create=True)

        self.parser = self.add_patch('parser')
        self.platform = self.add_patch('platform')

        self.command = helper.setupext.RunCommand(mock.Mock())
        self.command.controller = 'some.string'
        self.command.configuration = mock.sentinel.config_file_path
        self.command.run()

    def test_configuration_parameter_passed_to_parser(self):
        parser = self.parser.get.return_value
        parser.parse_args.assert_called_once_with(
            ['-f', '-c', mock.sentinel.config_file_path])
