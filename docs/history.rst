Version History
===============
2.1.0 - 2013-09-24 - Bugfixes: Use pidfile from configuration if specified, don't show warning about not having a logger in helper.unix if no logger is defined, config obj default/value assignment methodology
2.0.2 - 2013-08-28 - Fix a bug where wake_interval default was not used if wake_interval was not provided in the config. Make logging config an overlay of the default logging config.
2.0.1 - 2013-08-28 - setup.py bugfix
2.0.0 - 2013-08-28 - clihelper renamed to helper with a major refactor. Windows support still pending.