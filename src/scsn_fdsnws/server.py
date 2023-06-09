import cherrypy
from cherrypy.process.plugins import Daemonizer

import argparse
import datetime
import io
import os
import sys
from .archive import RingserverArchive


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
    def index(self, net, sta, cha, starttime, endtime, loc="", format="miniseed", nodata="204"):
        if format != "miniseed":
            raise Exception(f"only miniseed format is accepted.: {format}")

        if starttime.endswith(".000"):
            starttime = starttime[:-4]
        if starttime.endswith("Z"):
            starttime = starttime[:-1]
        starttime = f"{starttime}+00:00"
        if endtime.endswith(".000"):
            endtime = endtime[:-4]
        if endtime.endswith("Z"):
            endtime = endtime[:-1]
        endtime = f"{endtime}+00:00"
        start = datetime.datetime.fromisoformat(starttime)
        end = datetime.datetime.fromisoformat(endtime)
        if end - start > self.max_timerange:
            url = cherrypy.url(qs=cherrypy.request.query_string)
            cherrypy.response.status = 413
            return f"<html><body><h3>Request time window too large:</h3>\n<p>Max is {self.max_timerange}.</p>\n<a href={url}>{url}</a></body></html>"
        record_bytes = self.archive.query(net, sta, loc, cha, start, end)
        cherrypy.log(f"Len {net} {sta} {loc} {cha} {starttime} {endtime} {len(record_bytes)}")
        if len(record_bytes) > 0:
            cherrypy.log(f"found {len(record_bytes)} bytes")
            buffer = io.BytesIO()
            for rb in record_bytes:
                buffer.write(rb)
            out = buffer.getvalue()

            cherrypy.response.headers['Content-Type'] = 'application/vnd.fdsn.mseed'
            outname = f"{net}_{sta}_{loc}_{cha}.mseed"
            cherrypy.response.headers['Content-Disposition'] = f'attachment; filename="{outname}"'
            cherrypy.response.headers['Content-Length'] = len(out)
            return out
        else:
            cherrypy.log(f"No data, return {nodata}")
            if nodata == "404":
                cherrypy.response.status = 404
            else:
                cherrypy.response.status = 204
            url = cherrypy.url(qs=cherrypy.request.query_string)
            return f"<html><body><h3>No data found for request:</h3>\n<a href={url}>{url}</a></body></html>"

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
        }
    }
    cherrypy.tree.mount(DataSelect(archive, ringconf), '/fdsnws/dataselect/1/query', conf)
    cherrypy.tree.mount(Nav(), '/', conf)

    if args.daemon:
        d = Daemonizer(cherrypy.engine)
        d.subscribe()
    else:
        cherrypy.engine.start()
        cherrypy.engine.block()

if __name__ == '__main__':
    main()
