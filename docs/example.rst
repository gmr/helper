Getting Started
===============
Creating your first :mod:`helper` application is a fairly straightforward process:

#. Download and install helper via pip::

    pip install helper

#. Create a new application with the `new-helper` script which will create a stub project including the package directory, configuration file, init.d script for RHEL systems, and setup.py file::

    new-helper -p myapp

#. Open the controller.py file in myapp/myapp/ and you should have a file that looks similar to the following::

    """myapp

    Helper boilerplate project

    """
    import helper
    import logging
    from helper import parser

    DESCRIPTION = 'Project Description'
    LOGGER = logging.getLogger(__name__)

    class Controller(helper.Controller):
        """The core application controller which is created by invoking
        helper.run().

       """

        def setup(self):
            """Place setup and initialization steps in this method."""
            LOGGER.info('setup invoked')

        def process(self):
            """This method is invoked every wake interval as specified in the
            application configuration. It is fully wrapped and you do not need to
            manage state within it.

            """
            LOGGER.info('process invoked')

        def cleanup(self):
            """Place shutdown steps in this method."""
            LOGGER.info('cleanup invoked')


    def main():
        parser.description(DESCRIPTION)
        helper.start(Controller)



#. Extend the :meth:`Controller.proccess <helper.Controller.proccess>` method to put your core logic in place.

#. If you want to test your app without installing it, I often make a small script in the project directory, something like myapp/myapp.py that looks like the following::

    #!/usr/bin/env
    from myapp import controller
    controller.main()

#. Change the mode of the file to u+x and run it::

    chmod u+x myapp.py
    ./myapp.py -c etc/myapp.yml -f


That's about all there is to it. If you don't want to use the sleep/wake/process pattern but want to use an IOLoop, instead of extending :meth:`Controller.process <helper.Controller.process>`, extend :meth:`Controller.run <helper.Controller.run>`.
