import unittest

from helper import config


class ConfigDefaultTests(unittest.TestCase):

    def setUp(self):
        self.config = config.Config()

    def test_application(self):
        self.assertDictEqual(self.config.application, config.APPLICATION)

    def test_daemon(self):
        self.assertDictEqual(self.config.daemon, config.DAEMON)

    def test_logging(self):
        self.assertDictEqual(self.config.logging, config.LOGGING)

