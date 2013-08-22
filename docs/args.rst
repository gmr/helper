Adding Commandline Arguments
============================
If you would like to add additional command-line options, access helper's `argparse based parser <http://docs.python.org/3/library/argparse.html>`_ adding additional command line arguments as needed. The arguments will be accessible via the `Controller.args` attribute.

Example::

    from helper import parser

    p = parser.get()
    p.add_argument('-n', '--newrelic',
                   action='store',
                   dest='newrelic',
                   help='Path to newrelic.init for enabling NewRelic '
                        'instrumentation')
    p.add_argument('-p', '--path',
                   action='store_true',
                   dest='path',
                   help='Path to prepend to the Python system path')


You can also override the auto-assigned application name::

    from helper import parser

    parser.name('my-app')

And the default description::

    from helper import parser

    parser.description('My application rocks!')
