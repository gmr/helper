Signal Handling
===============
The :class:`clihelper.Controller <clihelper.Controller>` class will automatically setup and handle signals for your application.

At time of daemonization, clihelper registers handlers for four signals:

- :ref:`term`
- :ref:`hup`
- :ref:`usr1`
- :ref:`usr2`

Signals received call registered methods within the :class:`Controller <clihelper.Controller>` class. If you are using multiprocessing and have child processes, it is up to you to then signal your child processes appropriately.

.. _term:

Handling SIGTERM
----------------
In the event that your application receives a ``TERM`` signal, it will change the internal state of the :class:`Controller <clihelper.Controller>` class indicating that the application is shutting down. This may be checked for by checking for a True value from the attribute :meth:`Controller.is_stopping <clihelper.Controller.is_stopping>` Controller.is_stopping. During this type of shutdown, :meth:`Controller.cleanup <clihelper.Controller.cleanup>` will be invoked. This method is meant to be extended by your application for the purposes of cleanly shutting down your application.

.. _hup:

Handling SIGHUP
---------------
The behavior in ``HUP`` is to cleanly shutdown the application and then start it back up again. It will, like with ``TERM``, call the :meth:`Controller.stop <clihelper.Controller.stop>` method. Once the shutdown is complete, it will clear the internal state and configuration and then invoke :meth:`Controller.run <clihelper.Controller.run>`.

.. _usr1:

Handling SIGUSR1
----------------
If you would like to reload the configuration, sending a ``USR1`` signal to the parent process of the application will invoke the :meth:`Controller.reload_configuration <clihelper.Controller.reload_configuration>` method, freeing the previously help configuration data from memory and reloading the configuration file from disk. Because it may be desirable to change runtime configuration without restarting the application, it is advised to use the :meth:`Controller.config <clihelper.Controller.config>` property method to retrieve configuration values each time instead of holding config values as attributes.

.. _usr2:

Handling SIGUSR2
----------------
This is an unimplemented method within the :class:`Controller <clihelper.Controller>` class and is registered for convenience. If have need for custom signal handling, redefine the :meth:`Controller.on_signusr2 <clihelper.Controller.on_sigusr2>` method in your child class.

