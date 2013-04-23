# clihelper

The clihelper package is a command-line/daemon application wrapper package with
the aim of creating a consistent method of creating daemonizing applications.


clihelper uses SIGALARM and signal.pause() to control intervals where the
dameon should be idle. Do not mix use of SIGALARM unless you intend to redefine
the run method for use with an IO Loop or some other long running process.

See the configuration file example later in this document for more information.

## Installation

clihelper is availble via pypi.python.org. Using pip to install:

    pip install clihelper

## Documentation

Documenation is available at http://clihelper.readthedocs.org

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

## License

Copyright (c) 2012-2013, MeetMe
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
