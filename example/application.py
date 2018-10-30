#!/usr/bin/env python
import logging

import helper
from helper import controller, parser

DESCRIPTION = 'Project Description'
LOGGER = logging.getLogger('example')

__version__ = '0.1.0'


class Controller(controller.Controller):
    """The core application controller which is created by invoking
    helper.run().

   """

    def setup(self):
        """Place setup and initialization steps in this method."""
        LOGGER.info('setup invoked')

    def process(self):
        """This method is invoked every wake interval as specified in the
        application configuration. It is fully wrapped and you do not need to
        manage state within it.

        """
        LOGGER.info('process invoked')

    def cleanup(self):
        """Place shutdown steps in this method."""
        LOGGER.info('cleanup invoked')


def main():
    parser.description(DESCRIPTION)
    helper.start(Controller)


if __name__ == '__main__':
    main()
