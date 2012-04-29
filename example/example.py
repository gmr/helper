#!/usr/bin/env python
"""
Example application

"""
__author__ = 'Gavin M. Roy'
__email__ = 'gmr@myyearbook.com'
__since__ = '2012-04-18'

import clihelper


class MyApp(clihelper.Controller):
    def _process(self):
        self._logger.info('Would be processing at the specified interval now')


if __name__ == '__main__':
    clihelper.setup('MyApp', 'MyApp is just a demo', '0.0.1')
    clihelper.run(MyApp)
