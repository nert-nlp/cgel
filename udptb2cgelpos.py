import conllu
import sys, re
sys.path.append('../')
import cgel
from cgel import Node
from collections import Counter
from math import log
from difflib import get_close_matches
from itertools import zip_longest

"""
Given EWT sentences with both UD and PTB trees, produce a tagged version for
CGEL tree annotation. The tagged version omits punctuation but includes gaps.
Heuristics are applied to guess the POS.
"""

OUTFORMAT = ['sentperline','tokperline'][0]

with open('datasets/ewt-test_pilot5.conllu') as f2:
    ud_trees = conllu.parse(f2.read())

# cgel_trees = []
# with open('../datasets/twitter.cgel') as f, open('../datasets/ewt.cgel') as f2:
#     for tree in cgel.trees(f2):
#         cgel_trees.append(tree)

def ud_tok_scanner(ud_tree):
    for node in ud_tree:
        if isinstance(node['id'], int): # skip token ranges
            yield node

def penn_tok_scanner(tree, allowed_empty=('*T*','*RNR*')):
    for x in tree.strip().splitlines():
        t = x.strip().split()[-1]
        t = t.replace('-LRB-','(').replace('-RRB-',')').replace('-LSB-','[').replace('-RSB-',']')
        if '-NONE-' not in x or t in allowed_empty:
            yield t

# upos ADV/cgel P: extracted from converter/ud-to-cgel.ini
ADV_P = set('''aboard|about|above|abroad|across|adrift|aft|after|afterward|afterwards|ago|aground|ahead|aloft|along|alongside|apart|around|as long as|as soon as|ashore|aside|at|away|back|backward|backwards|before|beforehand|behind|below|beneath|beside|besides|between|between|beyond|by|ceilingward|ceilingwards|despite|directly|downhill|downstairs|downstream|downtown|downward|downwards|downwind|due|during|earthwards|east|eastward|eastwards|else|elsewhere|far|fore|forth|forward|further|goalward|goalwards|heavenward|hence|here|home|homeward|immediately|in|indoors|inland|inside|instead|inward|inwards|landward|landwards|leeward|leftward|leftwards|near|nearby|nearer|nearest|next|north|northeast|northward|northwards|now|offline|on|online|onshore|onward|onwards|opposite|out|outdoors|outside|outward|outwards|over|overboard|overhead|overland|overnight|past|previous|prior|pursuant|rearward|rearwards|regardless|rightward|rightwards|round|seaward|seawards|shoreward|shorewards|sideward|sidewards|sideways|since|skyward|skywards|so|south|southeast|southward|southwards|sunward|sunwards|then|there|though|through|throughout|to|together|underfoot|underground|underneath|uphill|upstairs|upstream|upward|upwards|upwind|westward|westwards|when|whenever|where|whereabouts|windward|about|after|against|albeit|although|as|at|because|before|behind|besides|beyond|by|despite|due|ere|except|henceforth|if|in|lest|like|near|nearer|nearest|of|on|once|only|over|since|so|than|then|thereby|though|through|till|toward|towards|unless|unlike|until|up|upon|when|whence|whenever|where|whereas|whereby|wherein|whereupon|wherever|while|with'''.split('|'))

def cgelpos(tree, udnode):
    upos = udnode['upos']
    xpos = udnode['xpos']
    lemma = udnode['lemma']
    deprel = udnode['deprel']
    pardeprel = tree[udnode['head']-1]['deprel']

    if xpos=='TO':
        return 'Sdr'
    elif xpos in ('WDT','WP','WP$'):
        if lemma=='that':
            return 'Sdr'
        else:
            return {'PRON': 'Npro', 'DET': 'D'}[upos]
    elif xpos=='WRB':
        if lemma in ('why','how'):
            return 'Adv'
        else:
            return 'P'  # when, where, whenever, ...
    elif upos=='SCONJ':
        if lemma in ('that','whether'):
            return 'Sdr'
        elif lemma=='if' and pardeprel=='ccomp':
            return 'Sdr'
        else:
            return 'P'
    elif lemma in ('either','neither','both'):
        return 'D'
    elif xpos in ('DT','PDT'):
        return 'D'
    elif xpos=='JJ' and lemma in ('few','many','much'): # little is ambiguous
        return 'D'
    elif xpos=='RB' and lemma=='no':
        return 'D'
    elif xpos=='NN' and lemma=='none':
        return 'D'
    elif xpos=='NN' and upos=='PRON':
        return 'D'  # someone, ...
    elif xpos=='RB' and lemma in ('anywhere','everywhere','somewhere','nowhere'):
        return 'D'
    elif upos=='PART':
        if lemma=='not':
            return 'Adv'
        else:
            assert False,(lemma,upos,xpos)
    elif upos=='ADV' and lemma in ADV_P:
        return 'P'
    else:
        return {'ADJ': 'Adj', 'ADP': 'P', 'ADV': 'Adv', 'AUX': 'Vaux',
            'CCONJ': 'Coordinator', 'DET': 'D', 'INTJ': 'Int',
            'NOUN': 'N', 'NUM': 'D', 'PRON': 'Npro', 'PROPN': 'N', 'SYM': 'N',
            'VERB': 'V', 'X': 'N'}[upos]


# see "complex lexical items" in CGELBank manual
D_MWES = {'a certain','a few','a little','many a','no one'}    # NB: "a little" is ambiguous
# omitting "a great many" because it's a trigram
# TODO: also handle complex prepositions/other connectives? they are rare
for tree in ud_trees:
    # Look up Penn tree
    sentid = tree.metadata['sent_id']
    genre, docid, sentnum = sentid.split('-')
    assert genre in ('answers','email','newsgroup','reviews','weblog')
    sentnum = int(sentnum)
    with open(f'analysis/ewtdata/{genre}/penntree/{docid}.xml.tree') as pennF:
        for i,ln in zip(range(sentnum), pennF):
            otree = ln.strip()

    #s = tree.metadata['text']
    ptree = re.sub(r'[)]+', '\n', otree)
    penntoks = list(penn_tok_scanner(ptree))
    penntoksI = iter(penntoks)

    words = []
    tags = []
    for node in ud_tok_scanner(tree):
        ptok = next(penntoksI,'')
        while ptok in ('*T*','*RNR*'):
            words.append('_.')
            tags.append('GAP.x')
            ptok = next(penntoksI)

        upos = node['upos']
        xpos = node['xpos']
        lemma = node['lemma']
        if upos=='PUNCT' or xpos==',': continue # some SYM tokens are xpos=,

        # determine the CGEL wordform

        # default to CorrectForm if present, else surface form
        form = (node['misc'] or {}).get('CorrectForm',node['form'])

        # normalize casing a bit
        if lemma.lower()==form.lower():
            form = lemma
        elif lemma.islower():
            form = form.lower()

        # merge with previous token
        if node['deprel']=='goeswith' or (upos=='PART' and (lemma=="'s" or form=="n't")):
            words[-1] += form
            continue
        if words and words[-1].lower()+' '+lemma in D_MWES:
            words[-1] += '++'+lemma # ++ as separator within complex lexeme
            tags[-1] = 'D'
            continue

        # CGEL POS
        cpos = cgelpos(tree, node)
        words.append(form)
        tags.append(cpos)

    # print the tagged sentence
    for w,t in zip(words,tags):
        print(f'{w}/{t}', end=' ' if OUTFORMAT=='sentperline' else '\n')
    if OUTFORMAT=='sentperline':
        print()
