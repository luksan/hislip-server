========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis|
        | |codecov|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|

.. |docs| image:: https://readthedocs.org/projects/hislip-server/badge/?style=flat
    :target: https://readthedocs.org/projects/hislip-server
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/luksan/hislip-server.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/luksan/hislip-server

.. |codecov| image:: https://codecov.io/github/luksan/hislip-server/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/luksan/hislip-server

.. |version| image:: https://img.shields.io/pypi/v/hislip-server.svg
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/hislip-server

.. |commits-since| image:: https://img.shields.io/github/commits-since/luksan/hislip-server/v0.1.0.svg
    :alt: Commits since latest release
    :target: https://github.com/luksan/hislip-server/compare/v0.1.0...master

.. |wheel| image:: https://img.shields.io/pypi/wheel/hislip-server.svg
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/hislip-server

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/hislip-server.svg
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/hislip-server

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/hislip-server.svg
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/hislip-server


.. end-badges

A Python module implementing a HiSLIP server, to be integrated in other software.

* Free software: BSD license

Installation
============

::

    pip install hislip-server

Documentation
=============

https://hislip-server.readthedocs.io/

Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
