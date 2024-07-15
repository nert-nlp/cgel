import yaml
import re
import sys
from typing import Mapping
from collections import defaultdict
from yaml.representer import Representer

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

"""
From the YAML file, extracts unproblematic sentences
with no metalinguistic markers (* or brackets or slashes etc.),
stripping out HTML.
"""

RE_SIMPLE_ENTRY_ID = re.compile(r'^<em>.*?</em>')
def clean_entry(s):
    s = s.replace('</em> <double-u>', ' ').replace('</em><double-u>', '').replace('</double-u> <em>', ' ').replace('</double-u><em>', '')
    m = RE_SIMPLE_ENTRY_ID.search(s)
    if m is None or m.end()<len(s):
        return None # not a clean sentence
    return re.sub(r'<.*?>', '', s)  # delete all HTML tags



def recurse(d: Mapping):
    for k,v in d.items():
        if k=='page' or k=='title': continue
        if isinstance(v, list):
            entries = [e for e in v if not e.startswith(('<preTag>','<postTag>'))]
            globalexid = entries[0]
            for i,x in enumerate(entries[1:], start=1):
                if (y := clean_entry(x)):
                    exid = globalexid
                    if len(entries)>2:
                        exid += f'.{i}'
                    yield (exid, y)
        else:
            yield from recurse(v)


with (open(sys.argv[1]) if sys.argv[1:] else sys.stdin) as inF:
    doc = yaml.load(inF, Loader)
    for v in list(doc.values()):
        for (globalexid, y) in recurse(v):
            print(globalexid, y, sep='\t')
