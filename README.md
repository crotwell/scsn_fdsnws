# scsn_fdsnws
Simple implementation of FDSN web services using python.

FDSN web service specifications are available at:
[https://www.fdsn.org/webservices/]

# Configuration

Configuration is in a toml file. The pattern for the miniseed archive is given
in the `[mseed]` group as:
```
[mseed]

# MSEED Write pattern, usage similar to MSeedWrite in ringserver
# %n - network
# %s - station
# %l - location
# %c - channel
# %Y - year
# %j - day of year
# %H - hour
MSeedWrite='/data/scsn/www/mseed/%n/%s/%Y/%j/%n.%s.%l.%c.%Y.%j.%H'
```

# Run
```
scsnfdsnws -c fdsnws.toml
```
