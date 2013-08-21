"""
Command line argument parsing

"""
import argparse


def name(value):
    """A string providing an override of the name of the application from what
    is obtained from sys.argv[0].
    (default: sys.argv[0])

    :param str value: Name value

    """
    global _parser
    _parser.name = value


def description(value):
    """A string providing a description of the application
    (default: none)

    :param str value: Description value

    """
    global _parser
    _parser.description = value


def epilog(value):
    """Text to display after the description of the arguments
    (default: none)

    :param str value: Epilog value

    """
    global _parser
    _parser.epilog = value


def usage(value):
    """The string describing the program usage
    (default: generated from arguments added to parser)

    :param str value: Usage value

    """
    global _parser
    _parser.usage = value


def get():
    """Return the handle to the argument parser.

    :rtype: argparse.ArgumentParser

    """
    return _parser


def _add_default_arguments(parser):
    """Add the default arguments to the parser.

    :param argparse.ArgumentParser parser: The argument parser

    """
    parser.add_argument('-c', '--config',
                        action='store',
                        dest='config',
                        help='Path to the configuration file')
    parser.add_argument('-f', '--foreground',
                        action='store_true',
                        dest='foreground',
                        help='Run the application interactively')


def parse():
    """Parse the command line arguments and return the result

    :rtype: argparse.Namespace

    """
    global _parser
    return _parser.parse_args()


_parser = argparse.ArgumentParser()
_add_default_arguments(_parser)
