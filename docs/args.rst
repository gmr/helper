Adding Commandline Arguments
============================
If you would like to add additional command-line options, create a method that will receive one argument, parser. The parser is the OptionParser instance and you can add OptionParser options like you normally would. The command line options and arguments are accessible as attributes in the Controller: Controller._options and Controller._arguments::

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
