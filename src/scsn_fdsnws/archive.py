import datetime
import simplemseed
import pathlib
import re
import cherrypy

class RingserverArchive(object):
    def __init__(self, config):
        self.config = config
        self.configure_defaults(config)

    def files_for_request(self, net, sta, loc, chan, start, end):
        pattern = self.config["mseed"]["MSeedWrite"]
        if pattern is None:
            raise Exception("MSeedWrite is not in config")
        if loc == "--":
            loc = ""
        pattern = pattern.replace("%n", net)
        pattern = pattern.replace("%s", sta)
        pattern = pattern.replace("%l", loc)
        pattern = pattern.replace("%c", chan)
        search_hour = start.replace(microsecond=0, second=0, minute=0)
        hour = datetime.timedelta(hours=1)
        filelist = []
        while search_hour < end:
            filelist.append(search_hour.strftime(pattern))
            search_hour += hour
        return filelist
    def validate(self, net, sta, loc, chan, starttime, endtime):
        return isAlphaNum(net) and len(net) <= 2 \
            and isAlphaNum(sta) and len(sta) <=5 \
            and isAlphaNum(loc) and len(loc) <=2 \
            and isAlphaNum(chan) and len(chan)<=3 \
            and isinstance(starttime, datetime.datetime) \
            and isinstance(endtime, datetime.datetime)
    def query(self, net, sta, loc, chan, starttime, endtime):
        if not self.validate(net, sta, loc, chan, starttime, endtime):
            raise Exception("Illegal parameters")
        file_list = self.files_for_request(net, sta, loc, chan, starttime, endtime)
        records = []
        outbytes = []
        for mseedfile in file_list:
            f = pathlib.Path(mseedfile)
            cherrypy.log(f"load from {f}")
            if f.exists():
                try:
                    with open(f, "rb") as infile:
                        while True:
                            bytedata = infile.read(512)
                            if (len(bytedata) < 512):
                                break
                            msr = simplemseed.unpackMiniseedRecord(bytedata)

                            if not (msr.starttime() > endtime or msr.endtime() < starttime):
                                outbytes.append(bytedata)
                except simplemseed.MiniseedException as e:
                    cherrypy.log(f"possible corrupt file, skipping: {f}")
                    cherrypy.log(str(e))
        return outbytes


    def configure_defaults(self, conf):
        if "mseed" in conf:
            mseed_conf = conf["mseed"]
            if "MSeedWrite" not in mseed_conf:
                raise Exception("MSeedWrite pattern missing on mseed in configuration")
        if "ringserver" in conf:
            ring_conf = conf["ringserver"]
            if "port" not in ring_conf:
                ring_conf["port"] = 80
            if "host" not in ring_conf:
                ring_conf["host"] = "127.0.0.1"

alphanumRE = re.compile(r'[A-Z0-9-]*$')

def isAlphaNum(s):
    return alphanumRE.match(s) is not None
