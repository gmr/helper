# Helper

Helper is a development library for quickly writing configurable applications and daemons.


helper uses SIGALARM and signal.pause() to control intervals where the
dameon should be idle. Do not mix use of SIGALARM unless you intend to redefine
the run method for use with an IO Loop or some other long running process.

See the configuration file example later in this document for more information.

## Installation

helper is availble via pypi.python.org. Using pip to install:

    pip install helper

## Documentation

Documenation is available at http://helper.readthedocs.org

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
