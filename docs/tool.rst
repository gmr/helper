Application Initialization Tool
===============================
helper comes with a command line tool `new-helper` which will create a stub helper application project with the following items:

- Python package for the application
- Stub application controller
- Basic configuration file
- RHEL based init.d script
- setup.py file for distributing the application

Usage::

    usage: new-helper [-h] [--version] PROJECT

When you run the application, a tree resembling the following is created::

    PROJECT/
        etc/
            PROJECT.initd
            PROJECT.yml
        PROJECT/
            __init__.py
            controller.py
        setup.py

Where PROJECT is the value you specify when running ``new-helper``.
