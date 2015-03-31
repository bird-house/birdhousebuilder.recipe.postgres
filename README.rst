********************************
birdhousebuilder.recipe.postgres
********************************

.. contents::

Introduction
************

``birdhousebuilder.recipe.postgres`` is a `Buildout`_ recipe to install and configure `Postgres`_ database with `Anaconda`_. 
**Postgres** will be deployed as a `Supervisor`_ service. 

The recipe is based on https://github.com/makinacorpus/makina.recipe.postgres.

This recipe is used by the `Birdhouse`_ project. 

.. _`Buildout`: http://buildout.org/
.. _`Anaconda`: http://continuum.io/
.. _`Supervisor`: http://supervisord.org/
.. _`Postgres`: http://www.postgresql.org/
.. _`Birdhouse`: http://bird-house.github.io/


Usage
*****

The recipe requires that Anaconda is already installed. It assumes that the default Anaconda location is in your home directory ``~/anaconda``. Otherwise you need to set the ``ANACONDA_HOME`` environment variable or the Buildout option ``anaconda-home``.

It installs the ``postgresql`` package from a conda channel in a conda environment named ``birdhouse``. The location of the birdhouse environment is ``.conda/envs/birdhouse``. It deploys a `Supervisor`_ configuration for **Postgres** in ``~/.conda/envs/birdhouse/etc/supervisor/conf.d/postgres.conf``. Supervisor can be started with ``~/.conda/envs/birdhouse/etc/init.d/supervisor start``.

The Postgres database files are by default in ``~/.conda/envs/birdhouse/var/lib/postgres``.

The recipe depends on ``birdhousebuilder.recipe.conda`` and ``birdhousebuilder.recipe.supervisor``.

Supported options
=================

The recipe supports the following options:

**anaconda-home**
   Buildout option with the root folder of the Anaconda installation. Default: ``$HOME/anaconda``.
   The default location can also be set with the environment variable ``ANACONDA_HOME``. Example::

     export ANACONDA_HOME=/opt/anaconda

   Search priority is:

   1. ``anaconda-home`` in ``buildout.cfg``
   2. ``$ANACONDA_HOME``
   3. ``$HOME/anaconda``

**port**
    Port used for Postgres. Default: 5433.

**pgdata**
    path to the database files. Default: ``~/.conda/envs/birdhouse/var/lib/postgres``

**initdb**
    Options for Postgres initialisation. Default: ``--auth=trust``

**cmds**
    **psql** commands to setup your database schema and users.
   

Example usage
=============

The following example ``buildout.cfg`` installs **Postgres** with Anaconda::

  [buildout]
  parts = postgres

  anaconda-home = /home/myself/anaconda

  [postgres]
  recipe = birdhousebuilder.recipe.postgres
  port = 5433
  cmds =
       createuser -p 5433 --createdb --no-createrole --no-superuser --login demo
       createdb -p 5433 --owner=demo demo

After installing with Buildout start the **Postgres** service with::

  $ cd /home/myself/.conda/envs/birdhouse
  $ etc/init.d/supervisord start  # start|stop|restart
  $ bin/supervisorctl status      # check that postgres is running





