"""Create a new clihelper application including setting up the setup.py file,
initial directory structure and virtual environment, if desired.

"""
import argparse
import logging
import os

from . import __version__

LOGGER = logging.getLogger(__name__)

DESCRIPTION = ('A tool to create a new clihelper application, including the '
               'directory structure, setup.py file and skeleton configuration')

CONFIG = """!YAML 1.2
---
Application:
    wake_interval: 60

Daemon:
    user: %(project)s
    group: daemon
    pidfile: /var/run/%(project)s.pid

Logging:
  loggers:
    %(project)s:
      handlers: [console]
      level: DEBUG
      propagate: true
"""

INITD = """\
#!/bin/bash
# chkconfig: 2345 99 60
# description: %(project)s
# processname: %(project)s
# config: /etc/sysconfig/%(project)s
# pidfile: /var/run/%(project)s.pid

# Source function library.
. /etc/init.d/functions

# Application
APP="/usr/bin/%(project)s"

# Configuration dir
CONFIG_DIR="/etc"

# PID File
PID_FILE="/var/run/newrelic/%(project)s.pid"

# Additional arguments
OPTS=""

if [ -f /etc/sysconfig/%(project)s ]; then
  # Include configuration
  . /etc/sysconfig/%(project)s
fi

# Configuration file
CONF="${CONF:-${CONFIG_DIR}/%(project)s.yml}"

if [ ! -f "${CONF}" ]; then
  echo -n $"cannot find %(project)s configuration file: '${CONF}'"
  failure $"cannot find %(project)s configuration file: '${CONF}'"
  echo
  exit 1
fi

OPTS="-c ${CONF} ${OPTS}"

dostatus() {
  [ -e "${PID_FILE}" ] || return 1

  local pid=$(cat ${PID_FILE})
  [ -d /proc/${pid} ] || return 1

  [ -z "$(grep $APP /proc/${pid}/cmdline)" ] && return 1
  return 0
}

start() {
  if [ ${EUID} -ne 0 ]; then
    echo -n $"you must be root"
    failure $"you must be root"
    echo
    return 1
  fi

  echo -n $"Starting ${APP}: "

  dostatus
  if [ $? -eq 0 ]; then
    echo -n $"cannot start $APP: already running (pid: $(cat ${PID_FILE}))";
    failure $"cannot start $APP: already running (pid: $(cat ${PID_FILE}))";
    echo
    return 1
  fi

  ${APP} ${OPTS} && success || failure
  RETVAL=$?

  echo
  return ${RETVAL}
}

stop() {
  if [ ${EUID} -ne 0 ]; then
    echo -n $"you must be root"
    failure $"you must be root"
    echo
    return 1
  fi

  echo -n $"Stopping ${APP}: "

  dostatus
  if [ $? -ne 0 ]; then
    echo -n $"cannot stop $APP: not running"
    failure $"cannot stop $APP: not running"
    echo
    return 1
  fi

  killproc -p "${PID_FILE}" "${APP}"
  RETVAL=$?
  [ $RETVAL -eq 0 ] && rm -f ${PID_FILE}
  echo
  return $RETVAL
}

restart() {
  stop
  start
}

case "$1" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  restart)
    restart
    ;;
  status)
    dostatus
    if [ $? -eq 0 ]; then
      echo $"$APP: running"
      RETVAL=0
    else
      echo $"$APP: not running"
      RETVAL=1
    fi
    ;;
  *)
    echo $"Usage: $0 {start|stop|status|restart}"
    RETVAL=2
    ;;
esac

exit $RETVAL
"""

CONTROLLER = """\"""%(project)s

clihelper boilerplate project

\"""
import clihelper
import logging

from %(project)s import __version__

LOGGER = logging.getLogger(__name__)

DESCRIPTION = 'Project Description for cli help'


class Controller(clihelper.Controller):
    \"""The core application controller which is created by invoking
    clihelper.run().

   \"""

    def setup(self):
        \"""Place setup and initialization steps in this method.\"""
        LOGGER.info('setup invoked')

    def process(self):
        \"""This method is invoked every wake interval as specified in the
        application configuration. It is fully wrapped and you do not need to
        manage state within it.

        \"""
        LOGGER.info('process invoked')

    def cleanup(self):
        \"""Place shutdown steps in this method.\"""
        LOGGER.info('cleanup invoked')


def main():
    clihelper.setup('%(project)s', DESCRIPTION, __version__)
    clihelper.run(Controller)

"""

SETUP = """from setuptools import setup
import os
import platform

requirements = ['clihelper']
test_requirements = ['mock', 'nose']
(major, minor, rev) = platform.python_version_tuple()
if float('!s.!s' ! (major, minor)) < 2.7:
    test_requirements.append('unittest2')

# Build the path to install the support files
base_path = '/usr/share/%(project)s'
data_files = dict()
data_paths = ['etc']
for data_path in data_paths:
    for dir_path, dir_names, file_names in os.walk(data_path):
        install_path = '!s/!s' ! (base_path, dir_path)
        if install_path not in data_files:
            data_files[install_path] = list()
        for file_name in file_names:
            data_files[install_path].append('!s/!s' ! (dir_path, file_name))
with open('MANIFEST.in', 'w') as handle:
    for path in data_files:
        for filename in data_files[path]:
            handle.write('include !s\\n' ! filename)


setup(name='%(project)s',
      version='1.0.0',
      packages=['%(project)s'],
      install_requires=requirements,
      test_suite='nose.collector',
      tests_require=test_requirements,
      data_files=[(key, data_files[key]) for key in data_files.keys()],
      zip_safe=True)

"""

class Project(object):

    DEFAULT_MODE = 0755
    DIRECTORIES = ['etc', 'tests']

    def __init__(self):
        self._parser = self._create_argument_parser()

    def _add_base_arguments(self, parser):
        """Add the base arguments to the argument parser.

        :param argparse.ArgumentParser parser: The parser to add arguments to

        """
        parser.add_argument('--version',
                            help='show the version number and exit',
                            action='version',
                            version='%(prog)s ' + __version__)

    def _add_required_arguments(self, parser):
        """Add the required arguments to the argument parser.

        :param argparse.ArgumentParser parser: The parser to add arguments to

        """
        parser.add_argument('project',
                            metavar='PROJECT',
                            help='The project to create')

    def _create_argument_parser(self):
        """Create and return the argument parser with all of the arguments
        and configuration ready to go.

        :rtype: argparse.ArgumentParser

        """
        parser = self._new_argument_parser()
        self._add_base_arguments(parser)
        self._add_required_arguments(parser)
        return parser

    def _create_base_directory(self):
        os.mkdir(self._arguments.project, self.DEFAULT_MODE)

    def _create_directories(self):
        self._create_base_directory()
        self._create_subdirectory(self._arguments.project)
        for directory in self.DIRECTORIES:
            self._create_subdirectory(directory)

    def _create_subdirectory(self, subdir):
        os.mkdir('%s/%s' % (self._arguments.project, subdir),
                 self.DEFAULT_MODE)

    def _create_package_init(self):
        with open('%s/%s/__init__.py' %
                  (self._arguments.project,
                   self._arguments.project), 'w') as init:
            init.write('"""%s"""\n\n__version__ = \'1.0.0\'' %
                       self._arguments.project)

    def _create_controller(self):
        with open('%s/%s/controller.py' %
                  (self._arguments.project,
                   self._arguments.project), 'w') as handle:
            handle.write(CONTROLLER % {'project': self._arguments.project})

    def _create_package_setup(self):
        setup_py = SETUP % {'project': self._arguments.project}
        with open('%s/setup.py' % self._arguments.project, 'w') as init:
            init.write(setup_py.replace('!', '%'))

    def _create_default_configuration(self):
        config = CONFIG % {'project': self._arguments.project}
        with open('%s/etc/%s.yml' %
                  (self._arguments.project,
                   self._arguments.project), 'w') as handle:
            handle.write(config.replace('!', '%'))

    def _create_initd_script(self):
        with open('%s/etc/%s.initd' %
                  (self._arguments.project,
                   self._arguments.project), 'w') as handle:
            handle.write(INITD % {'project': self._arguments.project})

    def _new_argument_parser(self):
        """Return a new argument parser.

        :rtype: argparse.ArgumentParser

        """
        return argparse.ArgumentParser(prog='clihelper-init',
                                       conflict_handler='resolve',
                                       description=DESCRIPTION)

    def run(self):
        self._arguments = self._parser.parse_args()
        self._create_directories()
        self._create_package_init()
        self._create_controller()
        self._create_package_setup()
        self._create_default_configuration()
        self._create_initd_script()
        print '%s created' % self._arguments.project


def main():
    initializer = Project()
    initializer.run()


if __name__ == '__main__':
    main()
