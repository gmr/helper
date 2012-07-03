#!/usr/bin/env python
"""
Example application

"""
__author__ = 'Gavin M. Roy'
__email__ = 'gmr@meetme.com'
__since__ = '2012-04-18'
import sys
sys.path.insert(0, '..')

import clihelper
import logging

logger = logging.getLogger('MyApp')


class MyApp(clihelper.Controller):
    def _process(self):
        logger.info('Would be processing at the specified interval now')


if __name__ == '__main__':
    clihelper.setup('MyApp', 'MyApp is just a demo', '0.0.1')
    clihelper.run(MyApp)
