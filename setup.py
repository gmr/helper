import platform
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

requirements = ['pyyaml']
tests_require = ['mock']

# Add Python 2.6 compatibility libraries
(major, minor, rev) = platform.python_version_tuple()
if float('%s.%s' % (major, minor)) < 2.7:
    requirements.append('argparse')
    requirements.append('logutils')
    tests_require.append('unittest2')

setup(name='helper',
      version='2.4.1',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Environment :: Console',
          'Environment :: MacOS X',
          'Environment :: No Input/Output (Daemon)',
          #'Environment :: Win32 (MS Windows)',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Natural Language :: English',
          'Operating System :: MacOS',
          #'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Operating System :: POSIX :: BSD',
          'Operating System :: POSIX :: Linux',
          'Operating System :: Unix',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.2',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: Implementation :: CPython',
          'Programming Language :: Python :: Implementation :: PyPy',
          'Topic :: Software Development :: Libraries',
          'Topic :: Software Development :: Libraries :: Python Modules'],
      description=('Development library for quickly writing configurable '
                   'applications and daemons'),
      long_description=open('README.rst').read(),
      license=open('LICENSE').read(),
      author='Gavin M. Roy',
      author_email='gavinmroy@gmail.com',
      url='https://helper.readthedocs.org',
      packages=['helper'],
      package_data={'': ['LICENSE', 'README.rst']},
      install_requires=requirements,
      tests_require=tests_require,
      zip_safe=True,
      entry_points={
          'distutils.commands': ['run_helper = helper.setupext:RunCommand'],
      })
