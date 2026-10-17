#!/usr/bin/env python3
# rotpts.py - rotation line helper: % ke saath index POINTS bhi (rule)
# r: {name, sym, chg30, conf} | tf: timesfm_forecasts.json ka dict
# quote-safe style: sirf single quotes


def rotline(r, tf):
    name = r.get('name') or '?'
    p = r.get('chg30') or 0
    txt = '%s %+.1f%%' % (name, p)
    lvl = {}
    for f in (tf.get('forecasts') or []):
        if f.get('symbol') and f.get('as_of_last_close'):
            lvl[f['symbol']] = f['as_of_last_close']
    L = lvl.get(r.get('sym'))
    if L and p:
        try:
            pts = L - L / (1.0 + p / 100.0)
            txt += ' (%+.0f pts)' % pts
        except ZeroDivisionError:
            pass
    return txt
