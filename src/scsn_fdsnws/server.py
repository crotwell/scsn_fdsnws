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
                'tools.staticdir.root': os.path.abspath(os.getcwd()),
                'tools.staticdir.on': True,
                'tools.staticdir.dir': './public',
                'tools.staticdir.index': 'index.html',
                'tools.trailing_slash.missing': True,
                #'tools.trailing_slash.on': False,
                'tools.trailing_slash.status': 301,
                "tools.staticdir.debug": "True",
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
    cherrypy.tree.mount(Nav(), '/', conf)

    if args.daemon:
        d = Daemonizer(cherrypy.engine)
        d.subscribe()
    else:
        cherrypy.engine.start()
        cherrypy.engine.block()

if __name__ == '__main__':
    main()
