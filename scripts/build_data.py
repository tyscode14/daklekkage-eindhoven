"""Build the static KNMI dataset for the storm & rain checker.

Downloads the KNMI daily station files (etmgeg_<STN>.zip, CC BY 4.0) and writes:
  data/stations.json            station list, coordinates, coverage, climate percentiles, top days
  data/<STN>/<YEAR>.json        compact daily values per station per year (from FIRST_YEAR)

Run:  python scripts/build_data.py            (all years)
      python scripts/build_data.py --recent   (only rewrite the last two years; used by the nightly Action)
Standard library only.
"""
import io, json, math, os, re, sys, time, urllib.request, urllib.parse, zipfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FIRST_YEAR = 2000
CLIM = (1991, 2020)  # climate reference period for percentiles
UA = {"User-Agent": "daklekkage-eindhoven data builder (+https://github.com/tyscode14/daklekkage-eindhoven)"}
STATIONS_API = "https://www.daggegevens.knmi.nl/klimatologie/daggegevens"
ZIP_URL = "https://cdn.knmi.nl/knmi/map/page/klimatologie/gegevens/daggegevens/etmgeg_{}.zip"
# order of values stored per day
FIELDS = ["FHX", "FHXH", "FXX", "FXXH", "DDVEC", "RH", "RHX", "RHXH"]


def http(url, data=None, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if getattr(e, "code", None) == 404:
                return None
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def station_list():
    """Station ids, names and coordinates from the KNMI daily-data service header."""
    body = urllib.parse.urlencode({"start": "20260101", "end": "20260101", "vars": "FHX", "stns": "ALL"}).encode()
    txt = http(STATIONS_API, body).decode("latin-1")
    out = []
    for line in txt.splitlines():
        m = re.match(r"#\s+(\d{3})\s+([\d.]+)\s+([\d.]+)\s+(-?[\d.]+)\s+(.+?)\s*$", line)
        if m:
            out.append(dict(id=int(m[1]), lon=float(m[2]), lat=float(m[3]), alt=float(m[4]), name=m[5].strip()))
    if len(out) < 30:
        raise SystemExit("station list looks wrong (%d stations)" % len(out))
    return out


def parse(raw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    lines = z.read(z.namelist()[0]).decode("latin-1").splitlines()
    hdr, rows = None, []
    for l in lines:
        if l.startswith("# STN,YYYYMMDD"):
            hdr = [h.strip() for h in l[2:].split(",")]
            continue
        if hdr is None or l.startswith("#") or not l.strip():
            continue
        p = dict(zip(hdr, (x.strip() for x in l.split(","))))
        rows.append(p)
    return rows


def ival(v):
    return int(v) if v not in ("", None) else None


def pct(vals, q):
    vals = sorted(v for v in vals if v is not None)
    if len(vals) < 3000:  # need ~10 years of data for a meaningful percentile
        return None
    k = (len(vals) - 1) * q
    return round(vals[int(math.floor(k))] + (vals[int(math.ceil(k))] - vals[int(math.floor(k))]) * (k - math.floor(k)))


def main():
    recent = "--recent" in sys.argv
    this_year = date.today().year
    os.makedirs(DATA, exist_ok=True)
    stations = station_list()
    meta_out = []
    for st in stations:
        raw = http(ZIP_URL.format(st["id"]))
        if not raw:
            print("  %s %s: no daily file" % (st["id"], st["name"]))
            continue
        rows = parse(raw)
        by_year = {}
        clim_fhx, clim_rh, clim_fxx = [], [], []
        top_wind, top_rain = [], []
        last_wind = last_rain = None
        first = None
        for r in rows:
            d = r["YYYYMMDD"]
            y = int(d[:4])
            vals = [ival(r.get(f)) for f in FIELDS]
            fhx, fxx, rh = vals[0], vals[2], vals[5]
            if CLIM[0] <= y <= CLIM[1]:
                clim_fhx.append(fhx)
                clim_fxx.append(fxx)
                clim_rh.append(0 if rh == -1 else rh)
            if y < FIRST_YEAR:
                continue
            if all(v is None for v in vals):
                continue
            first = first or d
            if fhx is not None:
                last_wind = d
                top_wind.append((fhx, d, fxx))
            if rh is not None:
                last_rain = d
                top_rain.append((rh, d, vals[6]))
            by_year.setdefault(y, {})[d[4:]] = vals
        if not by_year:
            print("  %s %s: no data since %d" % (st["id"], st["name"], FIRST_YEAR))
            continue
        sdir = os.path.join(DATA, str(st["id"]))
        os.makedirs(sdir, exist_ok=True)
        for y, days in by_year.items():
            if recent and y < this_year - 1:
                continue
            with open(os.path.join(sdir, "%d.json" % y), "w", encoding="utf-8") as f:
                json.dump({"fields": FIELDS, "days": days}, f, separators=(",", ":"))
        top_wind.sort(reverse=True)
        top_rain.sort(reverse=True)
        meta_out.append(dict(
            id=st["id"], name=st["name"], lat=st["lat"], lon=st["lon"], alt=st["alt"],
            first=first, last_wind=last_wind, last_rain=last_rain,
            years=sorted(by_year),
            p99=dict(fhx=pct(clim_fhx, .99), fxx=pct(clim_fxx, .99), rh=pct(clim_rh, .99)),
            p999=dict(fhx=pct(clim_fhx, .999), rh=pct(clim_rh, .999)),
            top_wind=[dict(d=d, fhx=v, fxx=g) for v, d, g in top_wind[:8]],
            top_rain=[dict(d=d, rh=v, rhx=x) for v, d, x in top_rain[:8]],
        ))
        print("  %s %-24s %s..%s wind:%s rain:%s" % (st["id"], st["name"], first, max(filter(None, [last_wind, last_rain])), last_wind, last_rain))
    meta = dict(
        source="KNMI daggegevens (etmgeg), https://www.knmi.nl/nederland-nu/klimatologie/daggegevens",
        license="CC BY 4.0, bron: KNMI",
        units="FHX/FXX in 0.1 m/s, RH/RHX in 0.1 mm (-1 = minder dan 0.05 mm), FHXH/FXXH/RHXH = uurvak in UT (1 = 00-01 UT)",
        climate_period="%d-%d" % CLIM,
        built=date.today().isoformat(),
        stations=meta_out,
    )
    with open(os.path.join(DATA, "stations.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, separators=(",", ":"))
    print("stations written:", len(meta_out))


if __name__ == "__main__":
    main()
