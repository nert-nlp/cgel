import yaml
import re
import sys
from typing import Mapping
from collections import Counter

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

RE_GLOBAL_EX_ID = re.compile(r'^ex[0-9]+')

def recurse(d: Mapping):
    firstFullLocator = None
    for k,v in d.items():
        if k=='page': continue
        if isinstance(v, list):
            globalexid = v[0]
            newexid = RE_GLOBAL_EX_ID.sub('', globalexid)
            v[0] = newexid
            if not firstFullLocator:
                firstFullLocator = newexid
        else:
            loc = recurse(v)
            if not firstFullLocator:
                firstFullLocator = loc
    return firstFullLocator


with (open(sys.argv[1]) if sys.argv[1:] else sys.stdin) as inF:
    doc = yaml.load(inF, Loader)
    for k in list(doc.keys()):
        globalexid = k
        v = doc[globalexid]
        newexid = recurse(v)
        del doc[globalexid]
        assert newexid not in doc,newexid
        doc[newexid] = v

print(yaml.dump(doc))
