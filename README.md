# clihelper

The clihelper package is a command-line/daemon application wrapper package with
the aim of creating a consistent method of creating daemonizing applications.

clihelper uses logging.config.dictConfig package to create a flexible method for
configuring the python standard logging module. If Python 2.6 is used,
logutils.dictconfig.dictConfig is used instead. For information on the dictConfig
format, see the Python Standard Library documentation on the subject:

  http://docs.python.org/library/logging.config.html

YAML is used for the configuration file for clihelper based applications. The
configuration files expects three sections:

- Application: This is where configuration specific to your application resides
- Deamon: There are core directives here for daemonization
- Logging: This is where the logging configuration is placed.

The configuration file will automatically be loaded and referenced for all the
required information to start your application.

The configuration may be reloaded at runtime by sending a USR1 signal to parent
process. See the Signal Behaviors section of the README for more information on
how signals impact application behavior.

See the configuration file example later in this document for more information.

## Installation

clihelper is availble via pypi.python.org. Using pip to install:

    pip install clihelper

## Example Use

    import clihelper
    import logging

    logger = logging.getLogger(__name__)


    class MyController(clihelper.Controller):

        def _setup(self):
            """This method is called when the cli.run() method is invoked."""
            pass

        def _process(self):
            """This method is called after every sleep interval. If the intention
            is to use an IOLoop instead of sleep interval based daemon, override
            the _loop method.

            """
            # Do whatever your application does here
            self._dothings()


    def main():
        clihelper.setup('myapp', 'myapp does stuff', '1.0.0')
        clihelper.run(MyController)

## Example Configuration

The example configuration file below has a DictCursor configuration, settings
for the daemon.DaemonContect object and a section for Application specific
configuration.

    %YAML 1.2
    ---
    Application:
        wake_interval: 60

    Daemon:
        user: daemon
        group: daemon
        pidfile: /var/run/myapp

    Logging:
        version: 1
        formatters:
            verbose:
              format: '%(levelname) -10s %(asctime)s %(process)-6d %(processName) -15s %(name) -10s %(funcName) -20s: %(message)s'
              datefmt: '%Y-%m-%d %H:%M:%S'
            syslog:
              format: " %(levelname)s <PID %(process)d:%(processName)s> %(name)s.%(funcName)s(): %(message)s"
        filters:
        handlers:
            console:
                class: logutils.colorize.ColorizingStreamHandler
                formatter: verbose
                level: INFO
                debug_only: true
            syslog:
                class: logging.handlers.SysLogHandler
                facility: local6
                address: /dev/log
                formatter: syslog
                level: INFO
        loggers:
            MyApp:
                level: DEBUG
                propagate: true
                handlers: [console, syslog]
            urllib3:
                level: ERROR
                propagate: true
        disable_existing_loggers: false
        incremental: false

Any configuration key under Application is available to you via the
Controller._get_config method.

* Note that the debug_only node of the Logging > handlers > console section is
not part of the standard dictConfig format. Please see the "Logging Caveats" section
below for more information.

### Invoking

To invoke your application, either add a shebang to the top line (#!/usr/bin/env python)
and the execute bit set on your file in the filesystem or call via the Python cli
specifically.

#### Invoking an application with a "/usr/bin/env python" shebang

    ./myapp.py --help

#### Invoking explicitly with Python via the cli

    python myapp.py --help

#### Default CLI Options

    Usage: usage: example.py -c <configfile> [options]

    MyApp is just a demo

    Options:
      -h, --help            show this help message and exit
      -c CONFIGURATION, --config=CONFIGURATION
                            Path to the configuration file.
      -f, --foreground      Run interactively in console

### Accessing Configuration

The following snippet grabs the Application -> wake_interval value and assumes
you would be calling self._get_config from your extended Controller.

    wake_interval = self._get_config('wake_interval')

## Adding command line options

If you would like to add additional command-line options, create a method that
will receive one argument, parser. The parser is the OptionParser instance and
you can add OptionParser options like you normally would. The command line options
and arguments are accessible as attributes in the Controller: Controller._options
and Controller._arguments.

    def setup_options(parser):
        """Called by the clihelper._cli_options method if passed to the
        Controller.run method.

        """
        parser.add_option("-d", "--delete",
                          action="store_true",
                          dest="delete",
                          default=False,
                          help="Delete all production data")

    def main():
        """Invoked by a script created by setup tools."""
        clihelper.setup('myapp', 'myapp does stuff', '1.0.0')
        clihelper.run(MyController, setup_options)

## Signal Behaviors

By default, clihelper automates much of the signal handling for you. At time of
daemonization, clihelper registers handlers for four signals:

- SIGTERM
- SIGHUP
- SIGUSR1
- SIGUSR2

Signals received call registered methods within the Controller class. If you are
using multiprocessing and have child processes, it is up to you to then signal
your child processes appropriately.

### Handling SIGTERM

In the event that your application receives a TERM signal, it will change the
internal state of the Controller class indicating that the application is
shutting down. This may be checked for by checking for a True value from the
attribute Controller.is_shutting_down. During this type of shutdown and
if you are running your application interactively and CTRL-C is pressed,
Controller._shutdown will be invoked. This method is meant to be extended
by your application for the purposes of cleanly shutting down your application.

### Handling SIGHUP

The behavior in SIGHUP is to cleanly shutdown the application and then start it
back up again. It will, like with SIGTERM, call the Controller._shutdown method.
Once the shutdown is complete, it will clear the internal state and configuration
and then invoke Controller._run.

### Handling SIGUSR1

If you would like to reload the configuration, sending a SIGUSR1 signal to the
parent process of the application will invoke the Controller._reload_configuration
method, freeing the previously help configuration data from memory and reloading
the configuration file from disk. Because it may be desirable to change runtime
configuration without restarting the application, it is adviced to use the
Controller._get_config method instead of holding config values as attributes.

### Handling SIGUSR2

This is an unimplemented method within the Controller class and is registered
for convenience. If have need for custom signal handling, redefine the
Controller._on_signusr2 method in your child class.

## Logging

### Caveats

In order to allow for customizable console output when running in the foreground
and no console output when daemonized, a "debug_only" node has been added to the
standard dictConfig format in the handler section. This method is evaluated in
the clihelper._setup_logging method and removed, if present, prior to passing
the dictionary to dictConfig if present.

If the value is set to true and the application is not running in the foreground,
the configuration for the handler and references to it will be removed from the
configuration dictionary.

### Troubleshooting

If you find that your application is not logging anything or sending output
to the terminal, ensure that you have created a logger section in your configuration
for your controller. For example if your Controller instance is named MyController,
make sure there is a MyController logger in the logging configuration.

## Requirements

 - logutils
 - python-daemon
 - pyyaml

## License

Copyright (c) 2012, MeetMe
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

 * Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
 * Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
 * Neither the name of the MeetMe nor the names of its contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
