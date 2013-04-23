Controller
==========
Extend the :class:`Controller <clihelper.Controller>` class with your own application implementing the :meth:`Controller.process <clihelper.Controller.process>` method. If you do not want to use sleep based looping but rather an IOLoop or some other long-lived blocking loop, redefine the :meth:`Controller.run <clihelper.Controller.run>` method.

:class:`Controller <clihelper.Controller>` maintains an internal state which is handy for ensuring the proper things are happening at the proper times. The following are the constants used for state transitions:

    - :attr:`Initializing <clihelper.Controller.STATE_INITIALIZING>`
    - :attr:`Active <clihelper.Controller.STATE_ACTIVE>`
    - :attr:`Idle <clihelper.Controller.STATE_IDLE>`
    - :attr:`Sleeping <clihelper.Controller.STATE_SLEEPING>`
    - :attr:`Stop Requested <clihelper.Controller.STATE_STOP_REQUESTED>`
    - :attr:`Stopping <clihelper.Controller.STATE_STOPPING>`
    - :attr:`Stopped <clihelper.Controller.STATE_STOPPED>`

When extending :class:`Controller <clihelper.Controller>`, if your class requires initialization or setup setups, extend the :meth:`Controller.setup <clihelper.Controller.setup>` method.

If your application requires cleanup steps prior to stopping, extend the :meth:`Controller.cleanup <clihelper.Controller.cleanup>` method.

.. autoclass:: clihelper.Controller
    :members:
    :undoc-members:
