"""
Windows platform support for running the application as a detached process.

"""
import platform
import subprocess
import sys

DETACHED_PROCESS = 8


def operating_system():
    """Return a string identifying the operating system the application
    is running on.

    :rtype: str

    """
    return '%s %s (%s)' % (platform.system(),
                           platform.release(),
                           platform.version())


class Daemon(object):
    """Daemonize the helper application, putting it in a forked background
    process.

    """
    def __init__(self, controller):
        raise NotImplementedError
        #args = [sys.executable]
        #args.extend(sys.argv)
        #self.pid = subprocess.Popen(args,
        #                            creationflags=DETACHED_PROCESS,
        #                            shell=True).pid
