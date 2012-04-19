from setuptools import setup

setup(name='clihelper',
      version='1.1.0',
      description='Internal Command-Line Application Wrapper',
      long_description=('clihelper is a wrapper for command-line daemons '
                        'providing a core Controller class and methods for '
                        'starting the application and setting configuration.'),
      author='Gavin M. Roy',
      author_email='gmr@meetme.com',
      url='https://github.com/Python/clihelper',
      py_modules=['cliapp'],
      install_requires=['couchconfig',
                        'logging-config',
                        'python-daemon',
                        'pyyaml'],
      tests_requires=['mock', 'unittest2'],
      zip_safe=True)
