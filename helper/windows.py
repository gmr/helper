"""
Windows platform support for running the application as a detached process.

"""
import multiprocessing
import subprocess
import sys

DETACHED_PROCESS = 8


class Daemon(object):

    def __init__(self, controller, user=None, group=None,
                 pid_file=None, prevent_core=None, exception_log=None):
        """Daemonize the controller, optionally passing in the user and group
        to run as, a pid file, if core dumps should be prevented and a path to
        write out exception logs to.

        :param helper.Controller controller: The controller to daaemonize & run
        :param str user: Optional username to run as
        :param str group: Optional group to run as
        :param str pid_file: Optional path to the pidfile to run
        :param bool prevent_core: Don't make any core files
        :param str exception_log: Optional exception log path

        """
        args = [sys.executable]
        args.extend(sys.argv)
        self.pid = subprocess.Popen(args,
                                    creationflags=DETACHED_PROCESS,
                                    shell=True).pid
