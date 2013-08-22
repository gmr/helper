"""
Unix daemonization support

"""
import atexit
import datetime
import grp
import logging
import os
from os import path
import pwd
import re
import subprocess
import sys
import traceback

LOGGER = logging.getLogger(__name__)


class Daemon(object):
    """Daemonize the helper application, putting it in a forked background
    process.

    """
    def __init__(self, controller):
        """Daemonize the controller, optionally passing in the user and group
        to run as, a pid file, if core dumps should be prevented and a path to
        write out exception logs to.

        :param helper.Controller controller: The controller to daaemonize & run

        """
        self.controller = controller
        self.pidfile_path = self._get_pidfile_path()

    def __enter__(self):
        """Context manager method to return the handle to this object.

        :rtype: Daemon

        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """When leaving the context, examine why the context is leaving, if it's
         an exception or what.

        """
        if exc_type and not isinstance(exc_val, SystemExit):
            LOGGER.error('Daemon context manager closed on exception: %r',
                         exc_type)

    def start(self):
        """Daemonize if the process is not already running."""
        if self._is_already_running():
            sys.exit(1)

        exception_log = self._get_exception_log_path()
        try:
            self._daemonize()
            self.controller.start()
        except Exception as error:
            with open(exception_log, 'a') as handle:
                timestamp = datetime.datetime.now().isoformat()
                handle.write('{:->80}\n'.format(' [START]'))
                handle.write('%s Exception [%s]\n' % (sys.argv[0], timestamp))
                handle.write('{:->80}\n'.format(' [INFO]'))
                handle.write('Interpreter: %s\n' % sys.executable)
                handle.write('CLI arguments: %s\n' % ' '.join(sys.argv))
                handle.write('Exception: %s\n' % error)
                handle.write('Traceback:\n')
                output = traceback.format_exception(*sys.exc_info())
                _dev_null = [(handle.write(line),
                             sys.stdout.write(line)) for line in output]
                handle.write('{:->80}\n'.format(' [END]'))
                handle.flush()
            sys.exit(1)

    def _is_already_running(self):
        """Check to see if the process is running, first looking for a pidfile,
        then shelling out in either case, removing a pidfile if it exists but
        the process is not running.

        """
        # Look for the pidfile, if exists determine if the process is alive
        if os.path.exists(self.pidfile_path):
            pid = open(self.pidfile_path).read().strip()
            try:
                os.kill(int(pid), 0)
                sys.stderr.write('Process already running as pid # %s\n' % pid)
                return True
            except OSError as error:
                LOGGER.debug('Found pidfile, no process # %s', error)
                os.unlink(self.pidfile_path)

        # Check the os for a process that is not this one that looks the same
        pattern = ' '.join(sys.argv)
        pattern = '[%s]%s' % (pattern[0], pattern[1:])
        try:
            output = subprocess.check_output('ps a | grep "%s"' % pattern,
                                             shell=True)
        except subprocess.CalledProcessError:
            return False
        pids = [int(pid) for pid in (re.findall(r'^([0-9]+)\s',
                                                output.decode('latin-1')))]
        pids.remove(os.getpid())
        if not pids:
            return False
        if len(pids) == 1:
            pids = pids[0]
        sys.stderr.write('Process already running as pid # %s\n' % pids)
        return True

    def _daemonize(self):
        """Fork into a background process and setup the process, copied in part
        from http://www.jejik.com/files/examples/daemon3x.py

        """
        LOGGER.info('Forking %s into the background', sys.argv[0])
        try:
            pid = os.fork()
            if pid > 0:
                    sys.exit(0)
        except OSError as error:
                raise OSError('Could not fork off parent: %s', error)

        # Set the user id
        uid = self._get_uid()
        if uid is not None:
            os.setuid(uid)

        # Set the group id
        gid = self._get_gid()
        if gid is not None:
            os.setgid(gid)

        # Decouple from parent environment
        os.chdir('/')
        os.setsid()
        os.umask(0)

        # Fork again
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as error:
            raise OSError('Could not fork child: %s', error)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # Automatically call self._remove_pidfile when the app exits
        atexit.register(self._remove_pidfile)
        self._write_pidfile()

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
            if os.access(path.dirname(exception_log), os.W_OK):
                return exception_log

        raise OSError('Could not find an appropriate place for a exception log')

    def _get_gid(self):
        """Return the group id for the specified group.

        :rtype: int

        """
        if not self.controller.config.daemon.group:
            return None
        return grp.getgrnam(self.controller.config.daemon.group).gr_gid

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
            if not os.access(path.dirname(pidfile), os.W_OK):
                raise ValueError('Cannot write to specified pid file path'
                                 ' %s' % pidfile)
            return pidfile

        app = sys.argv[0].split('/')[-1]

        for pidfile in ['%s/pids/%s.pid' % (os.getcwd(), app),
                         '/var/run/%s.pid' % app,
                         '/var/run/%s/%s.pid' % (app, app),
                         '/var/tmp/%s.pid' % app,
                         '/tmp/%s.pid' % app,
                         '%s.pid' % app]:
            if os.access(path.dirname(pidfile), os.W_OK):
                return pidfile

        raise OSError('Could not find an appropriate place for a pid file')

    def _get_uid(self):
        """Return the user id for the specified username

        :rtype: int

        """
        if not self.controller.config.daemon.user:
            return None
        return pwd.getpwnam(self.controller.config.daemon.user).pw_uid

    def _remove_pidfile(self):
        """Remove the pid file from the filesystem"""
        with open('/tmp/dbug.log', 'a') as handle:
            handle.write('Removing %s\n' % self.pidfile_path)
        try:
            os.unlink(self.pidfile_path)
        except OSError:
            pass

    def _write_pidfile(self):
        """Write the pid file out with the process number in the pid file"""
        with open(self.pidfile_path, "w") as handle:
            handle.write(str(os.getpid()))
