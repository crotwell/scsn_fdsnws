from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
from dateutil.tz import tzoffset
from dateutil.parser import parse
from dateutil.utils import default_tzinfo
import string
import cherrypy
import io

from .fdsn_error import FDSNWSError

@cherrypy.expose
class DataSelectWebService(object):

    def __init__(self, archive, conf={}):
        self.archive = archive
        self.conf = self.configure_defaults(conf)
        self.max_timerange = timedelta(hours=int(self.conf["dataselect"]["maxqueryhours"]))

    @cherrypy.tools.accept(media='application/vnd.fdsn.mseed')
    def GET(self, **params):
        valid_params = self.validate_params(params)
        if len(valid_params) == 2:
            cherrypy.response.status = valid_params[1]
            return valid_params[0]
        net, sta, loc, cha, start, end, format, nodata = valid_params
        record_bytes = self.archive.query(net, sta, loc, cha, start, end)
        if len(record_bytes) > 0:
            buffer = io.BytesIO()
            for rb in record_bytes:
                buffer.write(rb)
            out = buffer.getvalue()

            cherrypy.response.headers['Content-Type'] = 'application/vnd.fdsn.mseed'
            cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
            outname = f"{net}_{sta}_{loc}_{cha}_{self.filize_datetime(start)}.mseed"
            cherrypy.response.headers['Content-Disposition'] = f'attachment; filename="{outname}"'
            cherrypy.response.headers['Content-Length'] = len(out)
            return out
        else:
            cherrypy.log(f"No data, return {nodata}")
            if nodata == "404":
                status = 404
            else:
                status = 204

            url = cherrypy.url(qs=cherrypy.request.query_string)
            self.form_error_html(status, f"<h3>No data found for request:</h3>\n")


    @cherrypy.tools.accept(media='application/vnd.fdsn.mseed')
    def POST(self, **params):
        print(f"POST {len(params)}")
        self.form_error_html(500, f"<h3>No implement POST</h3>")


    def PUT(self, another_string):
        self.form_error_html(500, f"<h3>No implement PUT</h3>")


    def DELETE(self):
        self.form_error_html(500, f"<h3>No implement DELETE</h3>")

    def validate_params(self, params):
        start =  params.get("start",  params.get("starttime", None))
        end =  params.get("end",  params.get("endtime", None))
        if start is None or end is None:
            self.form_error_html(400, f"Start and end times are required. start: {start}, end: {end}")
        net =  params.get("net",  params.get("network", None))
        sta =  params.get("sta",  params.get("station", None))
        loc =  params.get("loc",  params.get("location", None))
        cha =  params.get("cha",  params.get("channel", None))
        if net is None or sta is None or loc is None or cha is None:
            self.form_error_html(400, f"Net, sta, loc and cha are required. net: {net}, sta: {sta}, loc: {loc}, cha: {cha}")

        format = params.get("format", "miniseed")
        if format != "miniseed":
            self.form_error_html(400, f"only miniseed format is accepted.: {format}")
        nodata = params.get("nodata", "204")
        if not ( nodata == "204" or nodata == "404" ):
            self.form_error_html(400, f"nodata must be 204 or 404: {nodata}")

        start = isoparse(start)
        start = start.replace(tzinfo=timezone.utc)
        end = isoparse(end)
        end = end.replace(tzinfo=timezone.utc)
        if end - start > self.max_timerange:
            self.form_error_html(413, f"<h3>Request time window too large:</h3>\n<p>Max is {self.max_timerange}.</p>\n")
        return (net, sta, loc, cha, start, end, format, nodata)

    def form_error_html(self, status_code, html_msg):
        """
        returns length 2 tuple with html, status_code
        """
        url = cherrypy.url(qs=cherrypy.request.query_string)
        raise FDSNWSError(status_code, f"<h3>Error</h3>\n{html_msg}\n<a href={url}>{url}</a>" )

    def filize_datetime(self, d):
        return d.strftime('%y-%m-%dT%H%M%S')


    def configure_defaults(self, conf):
        defaults = {
            "dataselect": {
                "maxqueryhours": "24",
            },
            "ringserver": {
                "host": "127.0.0.1",
                "port": "80",
            }
        }
        out = {}
        out.update(defaults)
        out.update(conf)
        return out


if __name__ == '__main__':

    conf = {

        '/': {

            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),

            'tools.sessions.on': True,

            'tools.response_headers.on': True,

            'tools.response_headers.headers': [('Content-Type', 'text/plain')],

        }

    }

    cherrypy.quickstart(StringGeneratorWebService(), '/', conf)
