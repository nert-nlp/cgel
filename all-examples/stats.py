import yaml
import re
import sys
from typing import Mapping
from collections import Counter

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

RE_EX_NUM = re.compile(r'^ex[0-9]+|\[[0-9]+\]$')
RE_QUALITY = re.compile(r'^([*!?%#]?)\[?\(?<')
RE_QUALITY_POSTSLASH = re.compile(r'/ ?([*!?%#]?)\[?\(?<')

lbls = set()
items = []
pretags = set()
posttags = []
subnum_ids = []
qualitymarks = Counter()
qualitymarks_postslash = Counter()

def recursive_count(d: Mapping):
    nSubnum = 0
    nItems = 0
    nPreTags = 0
    nPostTags = 0
    for k,v in d.items():
        if k=='page': continue
        if not RE_EX_NUM.match(k):
            lbls.add(k)
        if isinstance(v, list):
            nSubnum += 1
            subnum_ids.append(v[0])
            for x in v[1:]:
                if x.startswith('<preTag>'):
                    nPreTags += 1
                    pretags.add(x.replace('<preTag>','').replace('</preTag>',''))
                elif x.startswith('<postTag>'):
                    nPostTags += 1
                    posttags.append(x.replace('<postTag>','').replace('</postTag>',''))
                else:
                    nItems += 1
                    if len(items)<100:
                        items.append(x)
                    if (m := RE_QUALITY.search(x)):
                        qualitymarks[m.group(1)] += 1
                    if (m := RE_QUALITY_POSTSLASH.search(x)):
                        qualitymarks_postslash[m.group(1)] += 1
        else:
            s, i, pre, post = recursive_count(v)
            nSubnum += s
            nItems += i
            nPreTags += pre
            nPostTags += post
    return nSubnum, nItems, nPreTags, nPostTags


with (open(sys.argv[1]) if sys.argv[1:] else sys.stdin) as inF:
    doc = yaml.load(inF, Loader)
    keys = list(doc.keys())
    nSubnum, nItems, nPreTags, nPostTags = recursive_count(doc)


print(f'- {len(doc)} top-level numbers (unique IDs `{keys[0]}` - `{keys[-1]}`; identified in the text as [1], [2], etc., counting from 1 in each section)')
print('   * excludes numbered entries that are lexical lists, definitions, or trees')
print(f'- {nSubnum} (sub)numbered groupings with global IDs (`{subnum_ids[0]}` - `{subnum_ids[-1]}`)')
print(f'- {nItems} sentence(-like) linguistic items (some are phrases; some contain slashes)')
print(f'   * counts of item-initial quality marks: `{qualitymarks}`')
print(f'   * counts of post-slash quality marks: `{qualitymarks_postslash}`')
print(f'- {nPreTags} pre-tags')
print(f'- {nPostTags} post-tags')
print()
print('# Nonnumeric labels')
for lbl in sorted(lbls):
    print(f'- {lbl}')
print()
print('# Linguistic items (first 10)')
for itm in items[:10]:
    print(f'- {itm}')
print('- ...')
print()
print('# Pre-tags')
for tag in sorted(pretags):
    print(f'- {tag}')
print()
print('# Post-tags (first 30)')
for tag in posttags[:30]:
    print(f'- {tag}')
print('- ...')
