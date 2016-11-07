Helper
======
Helper is a development library for quickly writing configurable applications and daemons.

|Version| |Downloads| |Status|

Platforms Supported
-------------------
Python 2.6+, 3.2+ on Unix (POSIX) and Windows (in process) platforms.

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
Documentation is available at https://helper.readthedocs.io

Installation
------------
helper is available as a package from pypi.python.org for development purposes.
Normally, helper would be installed as a dependency from another application or
package.

History
-------
- 2.4.2 - 2016-11-07
   - Allow for 'root' section in logging config
   - Import reduce from functools to suport Python 3
- 2.4.1 - 2013-03-14
   - Fix fchmod literal call in Python 3
- 2.4.0
   - Better startup exception reporting, improved pidfile ownership
     handling, new run_helper command
- 2.3.0
   - umask fix
- 2.2.2
   - Minor setup.py fix for README.rst
- 2.2.2
   - Minor MANIFEST.in fix for README.rst
- 2.2.1
   - Minor setup.py fix for version number.
- 2.2.0
   - Add new attribute to describe operating system and environment to
     Controller and helper.unix, helper.windows.
- 2.1.1
   - Bugfix for dealing with stale pids
- 2.1.0
   - Bugfixes: Use pidfile from configuration if specified, don't show
     warning about not having a logger in helper.unix if no logger is
     defined, config obj default/value assignment methodology
- 2.0.2
   - Fix a bug where wake_interval default was not used if wake_interval
     was not provided in the config. Make logging config an overlay of the
     default logging config.
- 2.0.1
   - setup.py bugfix
- 2.0.0
   - clihelper renamed to helper with major refactoring, Windows support
     still a work in progress.

.. |Version| image:: https://img.shields.io/pypi/v/helper.svg?
   :target: https://pypi.python.org/pypi/helper

.. |Status| image:: https://img.shields.io/travis/gmr/helper.svg?
   :target: https://travis-ci.org/gmr/helper

.. |Downloads| image:: https://img.shields.io/pypi/dm/helper.svg?
   :target: https://pypi.python.org/pypi/helper
