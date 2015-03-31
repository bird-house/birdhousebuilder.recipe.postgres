# -*- coding: utf-8 -*-
# Buildout recipe to setup postgres with anaconda for Birdhouse.
#
# This recipe is based on https://github.com/makinacorpus/makina.recipe.postgres
#
# It is distributed under the GPL license (the same as in makina.recipe.postgres).

"""Recipe postgres"""
import logging
import os
import time
from random import choice

from birdhousebuilder.recipe import conda

pg_ctl_script = """#!/bin/sh
PGDATA=%s %s/pg_ctl $@
"""

psql_script = """#!/bin/sh
%s/psql $@
"""

class Recipe(object):
    """This recipe is used by zc.buildout"""

    def __init__(self, buildout, name, options):
        """options:
        
          - bin : path to bin folder that contains postgres binaries
          - port : port on wich postgres is started and listen
          - initdb : specify the argument to pass to the initdb command
          - cmds : list of psql cmd to execute after all those init
        
        """
        self.buildout, self.name, self.options = buildout, name, options
        options['location'] = options['prefix'] = os.path.join(
            buildout['buildout']['parts-directory'],
            name)

    def system(self, cmd):
        code = os.system(cmd)
        if code:
            error_occured = True
            raise RuntimeError('Error running command: %s' % cmd)

    def pgdata_exists(self):
        return os.path.exists(self.options['pgdata']) 

    def install(self):
        """installer"""
        self.logger = logging.getLogger(self.name)
        installed = []
        installed += list(self.install_pkgs())
        installed += list(self.install_pg())
        return tuple()

    def install_pkgs(self):
        script = conda.Recipe(
            self.buildout,
            self.name,
            {'pkgs': 'postgresql'})
        
        #mypath = os.path.join(self.prefix, 'var', 'lib', 'pywps', 'outputs', self.sites)
        #conda.makedirs(mypath)

        return script.install()
    
    def install_pg(self):
        self.create_bin_scripts()
        if not os.path.exists(self.options['location']):
            os.mkdir(self.options['location'])
        #Don't touch an existing database
        if self.pgdata_exists():
            self.stopdb()
            return self.options['location']
        self.stopdb()
        self.initdb()
        self.configure_port()
        self.startdb()
        self.do_cmds()
        self.stopdb()
        return self.options['location']

    def update(self):
        """updater"""
        self.logger = logging.getLogger(self.name)
        self.create_bin_scripts()
        if not self.pgdata_exists():
            self.stopdb()
            self.initdb()
            self.startdb()
            self.do_cmds()
        self.configure_port()
        self.stopdb()
        return self.options['location']

    def startdb(self):
        if os.path.exists(os.path.join(self.options.get('pgdata'),'postmaster.pid')):
            self.system('%s restart'%(self.bin_pg_ctl))
        else:
            self.system('%s start'%(self.bin_pg_ctl))
        # TODO: check if db is realy up
        time.sleep(10)

    def stopdb(self):
        if os.path.exists(os.path.join(self.options.get('pgdata'),'postmaster.pid')):
            self.system('%s stop'%(self.bin_pg_ctl))
            time.sleep(10)

    def isdbstarted(self):
        PIDFILE = os.path.join(self.options.get('pgdata'),'postmaster.pid')
        return os.path.exists(pg_ctl) and os.path.exists(PIDFILE)

    def create_bin_scripts(self):
        buildout_bin_path = self.buildout['buildout']['bin-directory']
        # Create a wrapper script for psql user and admin
        psql = os.path.join(buildout_bin_path,'psql')
        script = open(psql , 'w')
        script.write(psql_script % (self.options.get('bin')))
        script.close()
        os.chmod(psql, 0755)
        pg_ctl = os.path.join(buildout_bin_path,'pg_ctl')
        script = open(pg_ctl, 'w')
        script.write(pg_ctl_script % (self.options.get('pgdata'), self.options.get('bin')))
        script.close()
        os.chmod(pg_ctl, 0755)
        self.bin_pg_ctl = pg_ctl
        self.bin_psql = psql
        return pg_ctl, psql

    def initdb(self):
        initdb_options = self.options.get('initdb',None)
        bin = self.options.get('bin','')
        if initdb_options and not self.pgdata_exists():
            self.system('%s %s' % (os.path.join(bin, 'initdb'), initdb_options) )

    def configure_port(self):
        port = self.options.get('port',None)
        if not port: return None
        self.logger.warning( " !!!!!!!!!!!! " )
        self.logger.warning( " Warning port is not tested at the moment" )
        self.logger.warning( " !!!!!!!!!!!! " )
        # Update the port setting and start up the server
        #FIXME we need to get pgdata from initdb option
        conffile = os.path.join(self.options.get('pgdata'),'postgresql.conf')
        f = open(conffile)
        conf = ('port = %s' % port).join(f.read().split('#port = 5432'))
        f.close()
        open(conffile, 'w').write(conf)

    def do_cmds(self):
        cmds = self.options.get('cmds', None)
        bin = self.options.get('bin')
        if not cmds: return None
        cmds = cmds.split(os.linesep)
        for cmd in cmds:
            if not cmd: continue
            try: self.system('%s/%s' % (bin, cmd))
            except RuntimeError, e:
                self.logger.exception('could not run pg setup commands!')
        dest = self.options['location']
