"""
Unix daemonization support

"""
import daemon
import datetime
import grp
import lockfile
import logging
import os
from os import path
import pwd
import sys
import traceback

LOGGER = logging.getLogger(__name__)


class Daemon(object):

    def __init__(self, controller):
        """Daemonize the controller, optionally passing in the user and group
        to run as, a pid file, if core dumps should be prevented and a path to
        write out exception logs to.

        :param helper.Controller controller: The controller to daaemonize & run

        """
        self.controller = controller
        self._pidfile_path = self._get_pidfile_path()
        self._kwargs = self._get_kwargs()

    def __enter__(self):
        """Context manager method to return the handle to this object.

        :rtype: Daemon

        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """When leaving the context, examine why the context is leaving, if it's
         an exception or what.

        """
        if exc_type:
            LOGGER.error('Daemon context manager closed on exception')

    def start(self):
        """Daemonize"""
        exception_log = self._get_exception_log_path()
        try:
            with daemon.DaemonContext(**self._kwargs):
                self._write_pidfile()
                self.controller.start()
        except Exception as error:
            with open(exception_log, 'a') as handle:
                timestamp = datetime.datetime.now().isoformat()
                handle.write('\n%s [START]\n' % ['-' for pos in range(0, 80)])
                handle.write('%s Exception [%s]\n' % (sys.arg[0], timestamp))
                handle.write('%s\n' % ['-' for pos in range(0, 80)])
                handle.write('Interpreter: %s\n' % sys.executable)
                handle.write('CLI arguments: %s\n' % ' '.join(sys.argv))
                handle.write('Exception: %s\n' % error)
                handle.write('Traceback:\n')
                output = traceback.format_exception(*sys.exc_info())
                _dev_null = [(handle.write(line),
                             sys.stdout.write(line)) for line in output]
                handle.write('\n%s [END]\n' % ['-' for pos in range(0, 80)])
                self._remove_pidfile()
                sys.exit(1)
        self._remove_pidfile()

    def _get_exception_log_path(self, exception_log=None):
        """Return the normalized path for the connection log, raising an
        exception if it can not written to.

        :param str exception_log: The path the user passed in, if any
        :return: str
        :raises: ValueError
        :raises: OSError

        """
        if exception_log:
            if not os.access(exception_log, os.W_OK):
                raise ValueError('Cannot write to specified exception log path'
                                 ' %s' % exception_log)
            return exception_log

        for exception_log in ['/var/log/%s.errors' % sys.argv[0],
                              '/var/tmp/%s.errors' % sys.argv[0],
                              '/tmp/%s.errors' % sys.argv[0]]:
            if os.access(exception_log, os.W_OK):
                return exception_log

        raise OSError('Could not find an appropriate place for a exception log')

    def _get_gid(self, group):
        """Return the group id for the specified group.

        :param str group: The group name to get the id for
        :rtype: int

        """
        return grp.getgrnam(group).gr_gid

    def _get_uid(self, username):
        """Return the user id for the specified username

        :param str username: The user to get the UID for
        :rtype: int

        """
        return pwd.getpwnam(username).pw_uid

    def _get_pidfile_path(self, pidfile=None):
        """Return the normalized path for the pidfile, raising an
        exception if it can not written to.

        :param str pidfile: The user specified pid file, if any
        :return: str
        :raises: ValueError
        :raises: OSError

        """
        if pidfile:
            pidfile = path.abspath(pidfile)
            if not os.access(pidfile, os.W_OK):
                raise ValueError('Cannot write to specified pid file path'
                                 ' %s' % pidfile)
            return pidfile

        for pidfile in ['%s/pids/%s.pid' % (os.getcwd(), sys.argv[0]),
                         '/var/run/%s.pid' % sys.argv[0],
                         '/var/run/%s/%s.pid' % (sys.argv[0], sys.argv[0]),
                         '/var/tmp/%s.pid' % sys.argv[0],
                         '/tmp/%s.pid' % sys.argv[0]]:
            if os.access(path.abspath(pidfile), os.W_OK):
                return path.abspath(pidfile)

        raise OSError('Could not find an appropriate place for a pid file')

    def _get_kwargs(self):
        """Return the dictionary of keyword arguments for the daemon context.

        :return: dict
        :raises: ValueError

        """
        try:
            pidlock_file = lockfile.FileLock(self._pidfile_path)
        except lockfile.LockFailed as error:
            raise ValueError('Can not write PID lock file to %s: %s' %
                             (self._pidfile_path, error))

        return {'gid': self._get_gid(self.controller.config.daemon.group),
                'pidfile': pidlock_file,
                'prevent_core': self.controller.config.daemon.prevent_core,
                'uid': self._get_uid(self.controller.config.daemon.user)}

    def _remove_file(self, path):
        """Try and remove all remnants of the pid file if it exists."""
        try:
            if os.path.exists(path):
                os.unlink(path)
        except OSError:
            pass

    def _remove_pidfile(self):
        """Remove the pid file from the filesystem"""
        self._remove_file(self._pidfile_path)
        self._remove_pidlock_file()

    def _remove_pidlock_file(self):
        """Remove the pid lock file from the filesystem"""
        self._remove_file("%s.lock" % self._pidfile_path)

    def _write_pidfile(self):
        """Write the pid file out with the process number in the pid file"""
        with open(self._pidfile_path, "w") as handle:
            handle.write(str(os.getpid()))
