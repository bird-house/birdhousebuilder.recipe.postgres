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
from mako.template import Template

from birdhousebuilder.recipe import conda, supervisor

templ_pg_ctl = Template( "${prefix}/bin/pg_ctl -D ${pgdata} ${cmd}" )
templ_initdb = Template( "${prefix}/bin/initdb --pgdata=${pgdata} ${options}" )
templ_pg_config = Template(filename=os.path.join(os.path.dirname(__file__), "postgresql.conf"))
templ_pg_cmd = Template( "${prefix}/bin/postgres -D ${pgdata}" )

class Recipe(object):
    """This recipe is used by zc.buildout"""

    def __init__(self, buildout, name, options):
        """options:
        
          - port : port on wich postgres is started and listen
          - initdb : specify the argument to pass to the initdb command
          - cmds : list of psql cmd to execute after all those init
        
        """
        self.buildout, self.name, self.options = buildout, name, options
        b_options = buildout['buildout']
        
        self.prefix = self.options.get('prefix', conda.prefix())
        self.options['prefix'] = self.prefix

        self.options['pgdata'] = self.options.get('pgdata', os.path.join(self.prefix, 'var', 'lib', 'postgres'))
        self.pgdata = self.options['pgdata']
        self.options['port'] = self.options.get('port', '5433')
        self.options['initdb'] = self.options.get('initdb', '--auth=trust')

    def install(self):
        """installer"""
        self.logger = logging.getLogger(self.name)
        installed = []
        installed += list(self.install_pkgs())
        installed += list(self.install_pg_supervisor())
        installed += list(self.install_pg())
        return tuple()

    def install_pkgs(self):
        script = conda.Recipe(
            self.buildout,
            self.name,
            {'pkgs': 'postgresql'})
        return script.install()

    def install_pg_supervisor(self, update=False):
        script = supervisor.Recipe(
            self.buildout,
            self.name,
            {'program': 'postgres',
             'command': templ_pg_cmd.render( prefix=self.prefix, pgdata=self.pgdata ),
             'directory': self.pgdata
             })
        if update == True:
            script.update()
        else:
            script.install()
        return tuple()
    
    def install_pg(self):
        # Don't touch an existing database
        if self.pgdata_exists():
            return tuple()

        self.stopdb()
        self.initdb()
        self.configure_port()
        self.startdb()

        self.do_cmds()
        self.stopdb()
        return tuple()

    def update(self):
        """updater"""
        self.logger = logging.getLogger(self.name)
        if not self.pgdata_exists():
            self.stopdb()
            self.initdb()
            self.startdb()
            self.do_cmds()
        self.configure_port()
        self.stopdb()
        return tuple()

    # helper messages
    # ---------------
    
    def system(self, cmd):
        code = os.system(cmd)
        if code:
            error_occured = True
            raise RuntimeError('Error running command: %s' % cmd)

    def pgdata_exists(self):
        return os.path.exists( self.pgdata ) 

    def startdb(self):
        cmd = 'start'
        if self.is_db_started():
            cmd = 'restart'
        self.system( templ_pg_ctl.render(prefix=self.prefix, pgdata=self.pgdata, cmd='restart') )
        # TODO: check if db is realy up
        time.sleep(10)

    def stopdb(self):
        if self.is_db_started():
            self.system( templ_pg_ctl.render(prefix=self.prefix, pgdata=self.pgdata, cmd='stop') )
            time.sleep(10)

    def is_db_started(self):
        pidfile = os.path.join( self.pgdata, 'postmaster.pid')
        return os.path.exists( pidfile )

    def initdb(self):
        if not self.pgdata_exists():
            initdb = templ_initdb.render(
                prefix=self.prefix,
                options=self.options.get( 'initdb' ),
                pgdata=self.pgdata)
            self.system( initdb )

    def configure_port(self):
        result = templ_pg_config.render( port=self.options.get('port') )
        output = os.path.join(self.pgdata, 'postgresql.conf')
        conda.makedirs(os.path.dirname(output))

        with open(output, 'wt') as fp:
            fp.write(result)
        os.chmod(output, 0600)
        return [output]

    def do_cmds(self):
        cmds = self.options.get('cmds', None)
        if not cmds:
            return None
        cmds = cmds.split(os.linesep)
        for cmd in cmds:
            if not cmd:
                continue
            try:
                self.system('%s/bin/%s' % (self.prefix, cmd))
            except RuntimeError, e:
                self.logger.exception('could not run pg setup commands!')
