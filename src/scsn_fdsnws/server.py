import cherrypy
from cherrypy.process.plugins import Daemonizer

import argparse
import datetime
import io
import os
import sys
from .archive import RingserverArchive
from .dataselect import DataSelectWebService


# tomllib is std in python > 3.11 so do conditional import
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib



class Nav(object):
    @cherrypy.expose
    def index(self):
        return """<html>

          <head></head>

          <body>

            <form method="get" action="query">

              <input type="text" value="8" name="length" />

              <button type="submit">Give it now!</button>

            </form>

          </body>

        </html>"""

class DataSelect(object):
    def __init__(self, archive, conf={}):
        self.archive = archive
        self.conf = self.configure_defaults(conf)
        self.max_timerange = datetime.timedelta(hours=int(self.conf["dataselect"]["maxqueryhours"]))

    @cherrypy.expose
    def index(self):
        return """<html>

          <head></head>

          <body>
            <h3>SCSN FDSNWS service</h3>

          </body>

        </html>"""

    @cherrypy.expose
    def version(self):
        return f"""<html>

          <head></head>

          <body>
            <h3>SCSN FDSNWS service</h3>
            <h3>0.0.1</h3>
          </body>

        </html>"""

    @cherrypy.expose
    def echo(self, net, sta, loc, cha, starttime, endtime):
        cherrypy.log(f"echo {net}.{sta}.{loc}.{cha} {starttime} {endtime}")
        return f"""<html>

          <head></head>

          <body>
            <h3>SCSN FDSNWS service</h3>
            <h3>{net}.{sta}.{loc}.{cha} {starttime} {endtime}</h3>
          </body>

        </html>"""


    def configure_defaults(self, conf):
        if not "dataselect" in conf:
            conf["dataselect"] = {}
        dataselect_conf = conf["dataselect"]
        if "maxqueryhours" not in dataselect_conf:
            dataselect_conf["maxqueryhours"] = "24"
        if "ringserver" in conf:
            ring_conf = conf["ringserver"]
            if "port" not in ring_conf:
                ring_conf["port"] = 80
            if "host" not in ring_conf:
                ring_conf["host"] = "127.0.0.1"
        return conf





def do_parseargs():
    parser = argparse.ArgumentParser(
        description="Find gaps in miniseed archive and attempt to recover missing data."
    )
    parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="store_true"
    )
    parser.add_argument(
        "--daemon", help="run as daemon via fork", action="store_true"
    )
    parser.add_argument(
        "-c",
        "--conf",
        required=False,
        help="Configuration as TOML",
        type=argparse.FileType("rb"),
    )
    return parser.parse_args()

def main():

    args = do_parseargs()
    ringconf = tomllib.load(args.conf)
    args.conf.close()

    archive = RingserverArchive(ringconf)
    cherrypy.config.update({'server.socket_port': 9090})
    cherrypy.config.update({'server.socket_host': "0.0.0.0"})
    conf = {
            '/': {
                'tools.sessions.on': True,
                'tools.staticdir.root': os.path.abspath(os.getcwd())
            },
            '/static': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': './public'
            },
            '/fdsnws': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': './public'
            }
        }
    cherrypy.tree.mount(DataSelectWebService(archive, ringconf),
                        '/fdsnws/dataselect/1/query',
                        {'/': {
                                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                                'tools.trailing_slash.on': False,
                            }
                        }
                        )
    #cherrypy.tree.mount(DataSelect(archive, ringconf), '/fdsnws/dataselect/1', conf)
    cherrypy.tree.mount(Nav(), '/', conf)

    if args.daemon:
        d = Daemonizer(cherrypy.engine)
        d.subscribe()
    else:
        cherrypy.engine.start()
        cherrypy.engine.block()

if __name__ == '__main__':
    main()
