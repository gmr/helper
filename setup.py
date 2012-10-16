from setuptools import setup

setup(name='clihelper',
      version='1.4.7',
      description='Internal Command-Line Application Wrapper',
      long_description=('clihelper is a wrapper for command-line daemons '
                        'providing a core Controller class and methods for '
                        'starting the application and setting configuration.'),
      author='Gavin M. Roy',
      author_email='gmr@meetme.com',
      url='https://github.com/gmr/clihelper',
      py_modules=['clihelper'],
      install_requires=['logutils',
                        'python-daemon',
                        'pyyaml'],
      tests_require=['mock', 'unittest2'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Topic :: Software Development :: Libraries',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'License :: OSI Approved :: BSD License'],
      zip_safe=True)
