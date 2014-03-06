Setup Tools Integration
=======================
Helper installs an additional distutils command named *run_helper* that will run a :class:`Controller` directly from your *setup.py*.  This is a nice alternative to writing your our shell wrapper for use during development.  If *setup.py* is executable, then you can run ``myapp.Controller`` with::

    ./setup.py run_helper -c etc/myapp.yml -C myapp.Controller

This functionality is a standard *distutils* entry point so it follows all of the same rules as other extensions such as *build_sphinx* or *nosetests*.  The command line arguments can be included in the ``[run_helper]`` section of *setup.cfg*::

   [run_helper]
   configuration = etc/myapp.yml
   controller = myapp.Controller

