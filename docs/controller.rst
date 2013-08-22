Controller
==========
Extend the :class:`Controller <helper.Controller>` class with your own application implementing the :meth:`Controller.process <helper.Controller.process>` method. If you do not want to use sleep based looping but rather an IOLoop or some other long-lived blocking loop, redefine the :meth:`Controller.run <helper.Controller.run>` method.

:class:`Controller <helper.Controller>` maintains an internal state which is handy for ensuring the proper things are happening at the proper times. The following are the constants used for state transitions:

    - :attr:`Initializing <helper.Controller.STATE_INITIALIZING>`
    - :attr:`Active <helper.Controller.STATE_ACTIVE>`
    - :attr:`Idle <helper.Controller.STATE_IDLE>`
    - :attr:`Sleeping <helper.Controller.STATE_SLEEPING>`
    - :attr:`Stop Requested <helper.Controller.STATE_STOP_REQUESTED>`
    - :attr:`Stopping <helper.Controller.STATE_STOPPING>`
    - :attr:`Stopped <helper.Controller.STATE_STOPPED>`

When extending :class:`Controller <helper.Controller>`, if your class requires initialization or setup setups, extend the :meth:`Controller.setup <helper.Controller.setup>` method.

If your application requires cleanup steps prior to stopping, extend the :meth:`Controller.cleanup <helper.Controller.cleanup>` method.

.. autoclass:: helper.Controller
    :members:
    :undoc-members:
