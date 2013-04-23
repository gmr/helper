Troubleshooting
===============
If you find that you start your application and it immediately dies without any output on the screen, be sure to check for :ref:`unhandled`.

.. _unhandled:

Unhandled Exceptions
--------------------
By default clihelper will write any unhandled exceptions to a file in `/tmp/clihelper-exceptions.log`. You can change the path by altering :const:`clihelper.EXCEPTION_LOG <clihelper.EXCEPTION_LOG>` or turn this behavior off with :const:`clihelper.WRITE_EXCEPTION_LOG <clihelper.WRITE_EXCEPTION_LOG>` ``= False``.
