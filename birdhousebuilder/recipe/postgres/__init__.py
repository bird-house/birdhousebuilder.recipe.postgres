# -*- coding: utf-8 -*-
# Buildout recipe to setup postgres with anaconda for Birdhouse.
#
# This recipe is based on https://github.com/makinacorpus/makina.recipe.postgres
#
# It is distributed under the GPL license (the same as in makina.recipe.postgres).

"""Recipe postgres"""
import logging
import os
from subprocess import check_call
import shlex
from mako.template import Template

from birdhousebuilder.recipe import conda, supervisor

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
        self.logger = logging.getLogger(name)
        
        self.buildout, self.name, self.options = buildout, name, options
        b_options = buildout['buildout']
        
        self.prefix = self.options.get('prefix', conda.prefix())
        self.options['prefix'] = self.prefix

        self.options['pgdata'] = self.options.get('pgdata', os.path.join(self.prefix, 'var', 'lib', 'postgres'))
        self.pgdata = self.options['pgdata']
        conda.makedirs(os.path.dirname(self.pgdata))
        self.options['port'] = self.options.get('port', '5433')
        self.options['initdb'] = self.options.get('initdb', '--auth=trust')

    def install(self, update=False):
        installed = []
        installed += list(self.install_pkgs(update))
        installed += list(self.install_pg_supervisor(update))
        installed += list(self.install_pg())
        return tuple()

    def install_pkgs(self, update=False):
        script = conda.Recipe(
            self.buildout,
            self.name,
            {'pkgs': 'postgresql'})
        if update == True:
            script.update()
        else:
            script.install()
        return tuple()

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
        if self.pgdata_exists():
            # just update port
            self.configure_port()
        else:
            # initdb
            self.stopdb()
            self.initdb()
            self.configure_port()
            
            # apply user commands
            self.startdb()
            self.do_cmds()
            self.stopdb()
        return tuple()

    def update(self):
        return self.install(update=True)

    # helper messages
    # ---------------
    
    def pgdata_exists(self):
        return os.path.exists( self.pgdata )
    
    def pg_ctl(self, command=None, options=None):
        """
        pg_ctl document: http://www.postgresql.org/docs/current/static/app-pg-ctl.html
        """
        if command is not None:
            cmd = [os.path.join(self.prefix, 'bin', 'pg_ctl'), command, '-D', self.pgdata]
            cmd.append('-s')                # silent, only print errors
            cmd.extend( ['-w', '-t', '60'] ) # wait until operation completes, max time = 60 secs
            if command in ['stop', 'restart']:
                cmd.extend( ['-m', 'fast']) # fast shutdown, quit diretly with proper shutdown
            if command in ['init', 'initdb'] and options is not None:
                cmd.extend( ['-o', '"%s"' % options] ) # initdb options passed in quotes ""
            try:
                check_call( cmd )
            except:
                self.logger.exception('pg_ctl %s failed! cmd=%s', command, cmd)
                raise
    
    def startdb(self):
        if self.is_db_started():
            self.stopdb()
        self.pg_ctl('start')

    def stopdb(self):
        if self.is_db_started():
            self.pg_ctl('stop')

    def is_db_started(self):
        pidfile = os.path.join( self.pgdata, 'postmaster.pid')
        return os.path.exists( pidfile )

    def initdb(self):
        if not self.pgdata_exists():
            self.pg_ctl('initdb', self.options.get('initdb'))

    def configure_port(self):
        result = templ_pg_config.render( port=self.options.get('port') )
        output = os.path.join(self.pgdata, 'postgresql.conf')
        
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
                check_call( shlex.split( '%s/bin/%s' % (self.prefix, cmd)) )
            except:
                self.logger.exception('could not run pg setup commands!')
                raise
