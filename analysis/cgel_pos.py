import conllu
import sys
sys.path.append('../')
import cgel
from collections import Counter, defaultdict
from math import log
from difflib import get_close_matches

"""
Report stats on CGEL POSes only.
"""

def map_mult(s, olds, new):
    return new if any(o==s for o in olds) else s

with open('../datasets/twitter_ud.conllu') as f, open('../datasets/ewt_ud.conllu') as f2:
    ud_data = conllu.parse(f.read() + f2.read())

trees = []
with open('../datasets/twitter_cgel.txt') as f, open('../datasets/ewt_cgel.txt') as f2:
    a = ''.join([x for x in f.readlines() + f2.readlines() if x[0] in [' ', '(']])
    for tree in cgel.parse(a):
        trees.append(tree)
        #trees.append(conllu.parse(tree.to_conllu())[0])

cgel = Counter()
lemmas = Counter()
poses_by_lemma = defaultdict(set)
ambig_class = defaultdict(set)
fxn = {'D': set(), 'N_pro': set(), 'P': set(), 'Sdr': set(), 'Coordinator': set(), 'GAP': set()}

# node properties: 'constituent' (POS or phrasal category), 'deprel' (grammatical function), 'head' (index), 'label' (coindexation variable), 'text' (terminals only)
for cgel_tree in trees:
    for node in cgel_tree.tokens.values():
        if not node.text: continue  # not a terminal
        cgel_pos = node.constituent
        cgel[cgel_pos] += 1
        lemma = node.text.lower()
        if len(lemma)>3 and lemma.endswith("n't"):
            lemma = lemma[:-3]
        lemma = map_mult(lemma, ("'m", "am", "is", "are", "was", "were", "been", "being"), 'be')
        if cgel_pos=='P' and node.text=='am': # override the previous rule
            lemma = "a.m."
        if cgel_pos=='N_pro' and node.text=='out' and any(n.text=='garage/barn' for n in cgel_tree.tokens.values()): # typo
            lemma = "our"
        lemma = map_mult(lemma, ("has", "had", "having"), 'have')
        lemma = map_mult(lemma, ("does", "did", "doing"), 'do')
        lemma = map_mult(lemma, ("gets", "got", "gotten", "getting"), 'get')
        lemma = map_mult(lemma, ("takes", "took", "taken", "taking"), 'take')
        lemma = map_mult(lemma, ("comes", "came", "coming"), 'come')
        lemma = map_mult(lemma, ("goes", "went", "gone", "going"), 'go')
        lemma = map_mult(lemma, ("finds", "found", "finding"), 'find')
        lemma = map_mult(lemma, ("helps", "helped", "helping"), 'help')
        lemma = map_mult(lemma, ("tries", "tried", "trying"), 'try')
        lemma = map_mult(lemma, ("people",), 'person')
        lemma = map_mult(lemma, ("times",), 'time')
        lemmas[lemma] += 1
        poses_by_lemma[lemma].add(cgel_pos)
        if lemma in ('be',) and cgel_pos=='P':
            assert False,node
        if cgel_pos not in ('V','N','Adj','Adv',
            'Int','NP','PP','Nom','AdjP','Clause'): # data errors
            fxn[cgel_pos].add(lemma)

TOP_70 = dict([('be', 118), ('the', 100), ('to', 78), ('and', 66), ('a', 62), ('of', 50), ('i', 49), ('that', 46), ('have', 37), ('in', 35),
          ('it', 29), ('you', 25), ('for', 24), ('they', 22), ('we', 20), ('do', 18), ('on', 18), ('this', 18), ('my', 15), ('at', 14),
          ('with', 14), ('as', 14), ('your', 13), ('not', 13), ('get', 12), ('so', 12), ('he', 12), ('will', 11), ('just', 11), ('can', 11),
          ('all', 10), ('if', 10), ('take', 10), ('who', 9), ('there', 9), ('or', 9), ('but', 9), ("'s", 8), ('go', 8), ('what', 8),
          ('would', 8), ('new', 8), ('by', 8), ('an', 8), ('time', 8), ('like', 8), ('person', 7), ('out', 7), ('about', 7), ('more', 7),
          ('me', 7), ('from', 7), ('his', 7), ('call', 6), ('now', 6), ('their', 6), ('should', 6), ('could', 6), ('also', 6), ('any', 6),
          ('come', 6), ('find', 5), ('how', 5), ('want', 5), ('think', 5), ('very', 5), ('first', 5), ('try', 5), ('him', 5), ('our', 5)])
for lemma,poses in poses_by_lemma.items():
    if lemma in TOP_70:
        ambig_class[frozenset(poses)].add(lemma)

print(cgel)
#print(lemmas.most_common(70))
for k,v in ambig_class.items():
    print(set(k), ': ', ' '.join(v), sep='')
for k,v in fxn.items():
    print(f'{k:>11}', ': ', ', '.join(sorted(v)), sep='')
