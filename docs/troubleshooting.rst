Troubleshooting
===============
If you find that you start your application and it immediately dies without any output on the screen, be sure to check for :ref:`unhandled`.

.. _unhandled:

Unhandled Exceptions
--------------------
By default helper will write any unhandled exceptions to a file in one of the following paths:

UNIX:
- /var/log/<APPNAME>.errors
- /var/tmp/<APPNAME>.errors
- /tmp/<APPNAME>.errors

Windows:
- Not implemented yet.
