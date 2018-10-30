Getting Started
===============
Creating your first :mod:`helper` application is a fairly straightforward process:

#. Download and install helper via pip::

    pip install helper

#. Create a helper controller:

    """
    Helper Example
    ==============

    """
    import logging

    import helper
    from helper import controller, parser

    DESCRIPTION = 'Project Description'
    LOGGER = logging.getLogger(__name__)

    class Controller(controller.Controller):
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


    if __name__ == '__main__':
        main()


#. Extend the :meth:`Controller.process <helper.controller.Controller.process>` method to put your core logic in place.

That's about all there is to it. If you don't want to use the sleep/wake/process pattern but want to use an IOLoop,
instead of extending :meth:`Controller.process <helper.controller.Controller.process>`,
extend :meth:`Controller.run <helper.controller.Controller.run>`.
