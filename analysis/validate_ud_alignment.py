import conllu
import sys
sys.path.append('../')
import cgel
from collections import Counter
from itertools import chain

"""
Check the alignment of tokens between .cgel and .conllu files.
If the UD tokens are finer-grained, this should be reflected in :subt and :subp
parts of the CGEL token.
"""

with open('../datasets/twitter_ud.conllu') as f, open('../datasets/ewt_ud.conllu') as f2:
    ud_trees = conllu.parse(f.read() + f2.read())

cgel_trees = []
with open('../datasets/twitter.cgel') as f, open('../datasets/ewt.cgel') as f2:
    for tree in chain(cgel.trees(f),cgel.trees(f2)):
        cgel_trees.append(tree)

def ud_tok_scanner(ud_tree):
    for node in ud_tree:
        if isinstance(node['id'], int): # skip token ranges
            yield node

DIVERGENCES = {('considering/P', 'consider/VERB'), ('coupled/P', 'couple/VERB'),
    ('including/P', 'include/VERB'), ('regarding/P', 'regard/VERB'),
    ('your/N_pro', 'you/PRON'),
    ('-/Coordinator', '-/PUNCT')}

assert len(ud_trees)==len(cgel_trees)
iSent = 0
for ud_tree,cgel_tree in zip(ud_trees,cgel_trees):
    #print(cgel_tree.leaves())
    udI = ud_tok_scanner(ud_tree)
    for leaf in cgel_tree.leaves():
        if leaf.constituent=='GAP': continue
        if leaf.text: # non-gap terminal node
            # skip e.g. (Nom) in fused determiner-head NP
            # also skip insertion corrections (not present in UD)
            # standard words as well as deletion corrections
            for p in leaf.prepunct:
                udn = next(udI)
                assert udn['form']==p and udn['upos']=='PUNCT',(p,udn)

            if leaf.substrings: # align multiple UD words to this CGEL word
                for i,(typ,s) in enumerate(leaf.substrings):
                    udn = next(udI)
                    if typ==':subp':    # hyphen punctuation in UD omitted from CGEL version of the word. not currently used in the corpus
                        assert udn['form']==s=='-' and udn['upos']=='PUNCT',(s,udn)
                    else:
                        assert typ==':subt'
                        assert udn['form'].lower()==s.lower(),(leaf.text,leaf.lemma,leaf.constituent,udn)
                        if i==0 and not (s=='get' or (udn['upos']=='AUX')==(leaf.constituent=='V_aux')):
                            print('POS mismatch (could be due to existential):', leaf.text, leaf.constituent, cgel_tree.sent)

            else:   # 1-to-1 not counting surrounding punctuation
                udn = next(udI)
                assert udn['form'].lower()==leaf.text.lower(),(leaf.text,leaf.lemma,leaf.constituent,udn)
                udtagged = udn['lemma']+'/'+udn['upos']
                cgeltagged = (leaf.lemma or leaf.text)+'/'+leaf.constituent
                # Check lemmas match
                if leaf.lemma is not None:  # skip deleted token
                    if udn['upos']=='PRON' and (udn['feats'] or {}).get('Poss')=='Yes': # note that PRP$/WP$ doesn't include 'mine' etc.
                        assert leaf.lemma=={'my': 'I', 'mine': 'I', 'your': 'you', 'yours': 'you',
                                            'his': 'he', 'her': 'she', 'hers': 'she', 'its': 'it',
                                            'our': 'we', 'ours': 'we', 'their': 'they', 'theirs': 'they'}[udn['lemma']],(leaf.lemma,udn['lemma'],cgel_tree.sentid)
                    elif not (udn['lemma']==leaf.lemma or (cgeltagged,udtagged) in DIVERGENCES):
                        if udn['lemma'].lower()==leaf.lemma.lower():
                            print('Lemma capitalization divergence',cgeltagged,udtagged)
                        else:
                            assert False,(cgeltagged,leaf.correct,udtagged,cgel_tree.sent)
                assert udn['upos']!='PUNCT' or (cgeltagged,udtagged) in DIVERGENCES,(cgeltagged,udtagged)
                if not (leaf.lemma=='get' or (udn['upos']=='AUX')==(leaf.constituent=='V_aux')):
                    print('POS mismatch (could be due to existential):', leaf.text, leaf.constituent, cgel_tree.sent)

            for p in leaf.postpunct:
                udn = next(udI)
                assert udn['form']==p and udn['upos']=='PUNCT',(p,udn)
