# clihelper

The clihelper package is a command-line/daemon application wrapper package with
the aim of creating a consistent method of creating daemonizing applications.

clihelper uses the logging-config package to create a flexible method for
configuring the python standard logging module. For more information on
logging-config, see https://github.com/gmr/logging-config.

YAML is used for the configuration file for clihelper based applications. The
configuration files expects three sections:

- Application: This is where configuration specific to your application resides
- Deamon: There are core directives here for daemonization
- Logging: This is where the logging-config configuration is placed.

See the configuration file example later in this document for more information.

## Example Use

    import clihelper


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

        cli.setup('myapp', 'myapp does stuff', '1.0.0')
        cli.run(MyController)

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


## Example Configuration

The following JSON configuration snippets are documents in the
com_myyearbook_operations_myservice database in the CouchDB configuration system.

    %YAML 1.2
    ---
    Application:
        wake_interval: 60

    Daemon:
        user: daemon
        group: daemon
        pidfile: /var/run/myapp

    Logging:
        formatters:
            verbose: "%(levelname) -10s %(asctime)s %(process)-6d %(processName) -15s %(name) -25s %(funcName) -25s: %(message)s",
            syslog: " %(levelname)s <PID %(process)d:%(processName)s> %(name)s.%(funcName)s(): %(message)s"
        filters:
        handlers:
            console:
                class: logging.StreamHandler
                formatter: verbose
                level: INFO
            syslog:
                class: logging.handlers.SysLogHandler
                facility: local6
                address: /dev/log
                formatter: syslog
                level: INFO
        loggers:
            clihelper:
                level: DEBUG
                propagate: true
                handlers: [console, syslog]
            urllib3:
                level: ERROR
                propagate: true

Any configuration key under Application is available to you via the Controller._get_config method.

### Example

The following example assumes it is being called from your extended Controller and wants the variable "wake_interval" from the configuration.

    wake_interval = self._get_config('wake_interval')

## Requirements

 - logging-config
 - python-daemon
 - pyyaml

## License

Copyright (c) 2012, Meet Me
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

 * Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
 * Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
 * Neither the name of the Meet Me nor the names of its contributors may be used
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
