"""Add a setuptools command that runs a helper-based application."""
try:
    from setuptools import Command
except ImportError:
    from distutils.core import Command

try:
    from functools import reduce
except ImportError:
    pass  # use the builtin for py 2.x

from . import parser
from . import platform


class RunCommand(Command):

    """Run a helper-based application.

    This extension is installed as a ``distutils.commands``
    entry point that provides the *run_helper* command.  When
    run, it imports a :class:`helper.Controller` subclass by
    name, creates a new instance, and runs it in the foreground
    until interrupted.  The dotted-name of the controller class
    and an optional configuration file are provided as command
    line parameters.

    :param str configuration: the name of a configuration file
        to pass to the application *(optional)*
    :param str controller: the dotted-name of the Python class
        to load and run

    """

    description = 'run a helper.Controller'
    user_options = [
        ('configuration=', 'c', 'path to application configuration file'),
        ('controller=', 'C', 'controller to run'),
    ]

    def initialize_options(self):
        """Initialize parameters."""
        self.configuration = None
        self.controller = None

    def finalize_options(self):
        """Required override that does nothing."""
        pass

    def run(self):
        """Import the controller and run it.

        This mimics the processing done by :func:`helper.start`
        when a controller is run in the foreground.  A new instance
        of ``self.controller`` is created and run until a keyboard
        interrupt occurs or the controller stops on its own accord.

        """
        segments = self.controller.split('.')
        controller_class = reduce(getattr, segments[1:],
                                  __import__('.'.join(segments[:-1])))
        cmd_line = ['-f']
        if self.configuration is not None:
            cmd_line.extend(['-c', self.configuration])
        args = parser.get().parse_args(cmd_line)
        controller_instance = controller_class(args, platform)
        try:
            controller_instance.start()
        except KeyboardInterrupt:
            controller_instance.stop()
