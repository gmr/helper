import platform
from setuptools import setup
import pkg_resources

requirements = ['pyyaml']
tests_require = ['mock']
extras_require = {
    ':python_version == "2.6"': ['argparse', 'logutils'],
}

try:
    if 'bdist_wheel' not in sys.argv:
        for key, value in extras_require.items():
            if key.startswith(':') and pkg_resources.evaluate_marker(key[1:]):
                install_requires.extend(value)
except Exception:
    logging.getLogger(__name__).exception(
        'Something went wrong calculating platform specific dependencies, so '
        "you're getting them all!"
    )
    for key, value in extras_require.items():
        if key.startswith(':'):
            install_requires.extend(value)

if 'test' in sys.argv:
    (major, minor, rev) = platform.python_version_tuple()
    if float('%s.%s' % (major, minor)) < 2.7:
        tests_require.append('unittest2')

setup(name='helper',
      version='2.4.2',
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
      url='https://helper.readthedocs.io',
      packages=['helper'],
      package_data={'': ['LICENSE', 'README.rst']},
      install_requires=requirements,
      extras_require=extra_require,
      tests_require=tests_require,
      zip_safe=True,
      entry_points={
          'distutils.commands': ['run_helper = helper.setupext:RunCommand'],
      })
