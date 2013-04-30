Logging
=======
The :class:`Logging <clihelper.Logging>` class is included as a convenient wrapper to handle Python 2.6 and Python 2.7 dictConfig differences as well as to manage the :mod:`clihelper` specific ``debug_only`` Handler setting.

If you want to use the default console only logging for clihelper, you do not need to implement this configuration section. Any configuration you specify merges with the default configuration.

Default Configuration
---------------------
::

    disable_existing_loggers: true
    filters: {}
    formatters:
      verbose:
        datefmt: '%Y-%m-%d %H:%M:%S'
        format: '%(levelname) -10s %(asctime)s %(process)-6d %(processName) -15s %(threadName)-10s %(name) -25s %(funcName) -25sL%(lineno)-6d: %(message)s'
    handlers:
      console:
        class: logging.StreamHandler
        debug_only: true
        formatter: verbose
    incremental: false
    loggers:
      clihelper:
        handlers: [console]
        level: INFO
        propagate: true
    root:
      handlers: []
      level: 50
      propagate: true
    version: 1

.. autoclass:: clihelper.Logging
    :members:
