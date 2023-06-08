import datetime
import simpledali
import pathlib

class RingserverArchive(object):
    def __init__(self, config):
        self.config = config
        self.configure_defaults(config)

    def files_for_request(self, net, sta, loc, chan, start, end):
        pattern = self.config["mseed"]["MSeedWrite"]
        if pattern is None:
            raise Exception("MSeedWrite is not in config")
        pattern = pattern.replace("%n", net)
        pattern = pattern.replace("%s", sta)
        pattern = pattern.replace("%l", loc)
        pattern = pattern.replace("%c", chan)
        search_hour = start
        hour = datetime.timedelta(hours=1)
        filelist = []
        while search_hour < end:
            filelist.append(search_hour.strftime(pattern))
            search_hour += hour
        return filelist
    def query(self, net, sta, loc, chan, starttime, endtime):
        file_list = self.files_for_request(net, sta, loc, chan, starttime, endtime)
        records = []
        outbytes = []
        for mseedfile in file_list:
            f = pathlib.Path(mseedfile)
            if not f.parent.exists():
                raise Exception(f"Data dir for {f} doesn't exist!")
            if f.exists():
                with open(f, "rb") as infile:
                    while True:
                        bytedata = infile.read(512)
                        if (len(bytedata) < 512):
                            break
                        msr = simpledali.unpackMiniseedRecord(bytedata)

                        if not (msr.starttime() > endtime or msr.endtime() < starttime):
                            print(f"Found: {msr.starttime()}")
                            outbytes.append(bytedata)
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
