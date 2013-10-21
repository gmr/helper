try:
    import unittest2 as unittest
except ImportError:
    import unittest

from helper import config


class ConfigDefaultTests(unittest.TestCase):

    def setUp(self):
        self.config = config.Config()

    def test_application(self):
        self.assertDictEqual(self.config.application.dict(),
                             config.Config.APPLICATION)

    def test_daemon(self):
        self.assertDictEqual(self.config.daemon.dict(), config.Config.DAEMON)

    def test_logging(self):
        self.assertDictEqual(self.config.logging, config.Config.LOGGING)

