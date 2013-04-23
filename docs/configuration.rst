Configuration Format
====================
clihelper uses `logging.config.dictConfig <http://docs.python.org/library/logging.config.html>`_ module to create a flexible method for configuring the python standard logging module. If Python 2.6 is used, `logutils.dictconfig.dictConfig <https://pypi.python.org/pypi/logutils>`_ is used instead.

`YAML <http://yaml.org>`_ is used for the configuration file for clihelper based applications and will automatically be loaded and referenced for all the required information to start your application. The configuration may be reloaded at runtime by sending a USR1 signal to parent process.

The configuration file has three case-sensitive sections that are required: :ref:`application`, :ref:`daemon`, and :ref:`logging`.

.. _application:

Application
-----------
As a generalization, this is where your application's configuration directives go. There is only one core configuration attribute for this section, `wake_interval`. The `wake_interval` value is an integer value that is used for the sleep/wake/process flow and tells clihelper how often to fire the :meth:`Controller.process <clihelper.Controller.process>` method.

.. _daemon:

Daemon
------
This section contains the settings required to run the application as a daemon. They are as follows:

user
    The username to run as when the process is daemonized
group [optional]
    The group name to switch to when the process is daemonized
pidfile
    The pidfile to write when the process is daemonized
prevent_core
    This bool value tells clihelper if it can write core files or not when there is a major issue

.. _logging:

Logging
-------
As previously mentioned, the Logging section uses the Python standard library `dictConfig format <http://docs.python.org/library/logging.config.html>`_. The following basic example illustrates all of the required sections in the dictConfig format, implemented in YAML::

    version: 1
    formatters: []
    verbose:
      format: '%(levelname) -10s %(asctime)s %(process)-6d %(processName) -15s %(name) -10s %(funcName) -20s: %(message)s'
      datefmt: '%Y-%m-%d %H:%M:%S'
    handlers:
      console:
        class: logging.StreamHandler
        formatter: verbose
        debug_only: True
    loggers:
      clihelper:
        handlers: [console]
        level: INFO
        propagate: true
      myapp:
        handlers: [console]
        level: DEBUG
        propagate: true
    disable_existing_loggers: true
    incremental: false

.. NOTE::
    The debug_only node of the Logging > handlers > console section is not part of the standard dictConfig format. Please see the :ref:`caveats` section below for more information.

.. _caveats:

Logging Caveats
^^^^^^^^^^^^^^^
In order to allow for customizable console output when running in the foreground and no console output when daemonized, a "debug_only" node has been added to the standard dictConfig format in the handler section. This method is evaluated in the clihelper.Logging and removed, if present, prior to passing the dictionary to dictConfig if present.

If the value is set to true and the application is not running in the foreground, the configuration for the handler and references to it will be removed from the configuration dictionary.

Troubleshooting
^^^^^^^^^^^^^^^
If you find that your application is not logging anything or sending output to the terminal, ensure that you have created a logger section in your configuration for your controller. For example if your Controller instance is named MyController, make sure there is a MyController logger in the logging configuration.
