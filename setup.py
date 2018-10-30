from os import path
import setuptools


def read_requirements(name):
    requirements = []
    try:
        with open(path.join('requires', name)) as req_file:
            for line in req_file:
                if '#' in line:
                    line = line[:line.index('#')]
                line = line.strip()
                if line.startswith('-r'):
                    requirements.extend(read_requirements(line[2:].strip()))
                elif line and not line.startswith('-'):
                    requirements.append(line)
    except IOError:
        pass
    return requirements


setuptools.setup(
    name='helper',
    version='3.0.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Environment :: MacOS X',
        'Environment :: No Input/Output (Daemon)',
        # 'Environment :: Win32 (MS Windows)',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: MacOS',
        # 'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: BSD',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules'],
    description=('Development library for quickly writing configurable '
                 'applications and daemons'),
    long_description=open('README.rst').read(),
    license='BSD',
    author='Gavin M. Roy',
    author_email='gavinmroy@gmail.com',
    url='https://github.com/gmr/helper',
    packages=['helper'],
    package_data={'': ['LICENSE', 'README.rst']},
    install_requires=read_requirements('requires/installation.txt'),
    tests_require=read_requirements('requires/testing.txt'),
    zip_safe=True,
    entry_points={
        'distutils.commands': ['run_helper = helper.setupext:RunCommand']
    })
