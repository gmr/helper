Helper
======
Helper is a development library for quickly writing configurable applications and daemons.

Platforms Supported
-------------------
Python 2.6, 2.7, 3.2 and 3.3 on Unix (POSIX) and Windows (in process) platforms.

Dependencies
------------
*General*

 - pyyaml
 - argparse (Python 2.6 only)
 - logutils (Python 2.6 only)

*Testing*

 - mock
 - unittest2 (Python 2.6 only)

Documentation
-------------
Documentation is available at http://helper.readthedocs.org

Installation
------------
helper is available as a package from pypi.python.org for development purposes.
Normally, helper would be installed as a dependency from another application or
package.

History
-------
2.0.2 - Fix a bug where wake_interval default was not used if wake_interval was not provided in the config. Make logging config an overlay of the default logging config.
2.0.1 - setup.py bugfix
2.0.0 - clihelper renamed to helper with major refactoring, Windows support still
        a work in progress.
