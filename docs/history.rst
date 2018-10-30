Version History
===============
- 3.0.0 - 2018-03-14
   - Drop support for Python 2.6, 3.2, 3.3
   - Clean up signal handling to append signals to a queue to prevent signal handler locking issues
   - REMOVED `helper.Controller` alias for `helper.controller.Controller`

- 2.4.2 - 2015-11-04 - Allow for 'root' section in logging config
        - Import reduce from functools to suport Python 3
- 2.4.1 - 2013-03-14 - Fix fchmod literal call in Python 3
- 2.4.0 - 2013-03-13 - Better startup exception reporting, improved pidfile ownership handling, new run_helper command
- 2.3.0 - 2013-02-07 - Fix for umask handling
- 2.2.3 - 2013-10-21 - Minor MANIFEST.in fix for setup.py
- 2.2.2 - 2013-10-21 - Minor MANIFEST.in fix for README.rst
- 2.2.1 - 2013-10-21 - Minor setup.py version number fix
- 2.2.0 - 2013-10-21 - Add new attribute to describe operating system and environment to helper.Controller and helper.unix, helper.windows.
- 2.1.1 - 2013-10-10 - Bugfix for dealing with stale pids
- 2.1.0 - 2013-09-24 - Bugfixes: Use pidfile from configuration if specified, don't show warning about not having a logger in helper.unix if no logger is defined, config obj default/value assignment methodology
- 2.0.2 - 2013-08-28 - Fix a bug where wake_interval default was not used if wake_interval was not provided in the config. Make logging config an overlay of the default logging config.
- 2.0.1 - 2013-08-28 - setup.py bugfix
- 2.0.0 - 2013-08-28 - clihelper renamed to helper with a major refactor. Windows support still pending.
