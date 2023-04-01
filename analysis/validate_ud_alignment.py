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

ud_trees = []
for filename in ['twitter_ud.conllu', 'ewt_ud.conllu', 'ewt-test_pilot5.conllu', 'ewt-test_iaa50.conllu']:
    with open('../datasets/' + filename) as f:
        ud_trees.extend(conllu.parse(f.read()))

cgel_trees = []
for filename in ['twitter.cgel', 'ewt.cgel', 'ewt-test_pilot5.cgel', 'ewt-test_iaa50.cgel']:
    with open('../datasets/' + filename) as f:
        for tree in cgel.trees(f):
            cgel_trees.append(tree)

DIVERGENCES = {('considering/P', 'consider/VERB'), ('coupled/P', 'couple/VERB'),
    ('including/P', 'include/VERB'), ('regarding/P', 'regard/VERB'),
    ('your/N_pro', 'you/PRON'),
    ('-/Coordinator', '-/PUNCT')}

assert len(ud_trees)==len(cgel_trees)
iSent = 0
for ud_tree,cgel_tree in zip(ud_trees,cgel_trees):
    #print(cgel_tree.leaves())
    ud_tree = [n for n in ud_tree if isinstance(n['id'], int)]
    udI = iter(ud_tree)
    hold_word = hold_word2 = None
    for leaf in cgel_tree.leaves():
        if leaf.constituent=='GAP': continue
        if leaf.text: # non-gap terminal node
            # skip e.g. (Nom) in fused determiner-head NP
            # also skip insertion corrections (not present in UD)
            # standard words as well as deletion corrections
            for p in leaf.prepunct:
                if hold_word2:
                    udn = hold_word2
                    hold_word2 = None
                else:
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
                while True:
                    if hold_word2:
                        udn = hold_word2
                        hold_word2 = None
                    else:
                        udn = next(udI)

                    if udn['form'].lower()!=leaf.text.lower() and udn['xpos']=='$':
                        # currency symbol - hold for later due to reordering
                        #print('65>>', leaf, hold_word, hold_word2, repr(udn), file=sys.stderr)
                        hold_word = udn
                        continue
                    elif udn['form'].lower()!=leaf.text.lower() and hold_word:
                        # ready for the currency symbol
                        #print('69>>', leaf, hold_word, hold_word2, file=sys.stderr)
                        hold_word2 = udn
                        udn = hold_word
                        hold_word = None
                    assert udn['form'].lower()==leaf.text.lower(),(leaf.text,leaf.lemma,leaf.constituent,udn)
                    udtagged = udn['lemma']+'/'+udn['upos']
                    cgeltagged = (leaf.lemma or leaf.text)+'/'+leaf.constituent
                    # Check lemmas match
                    if leaf.lemma is not None:  # skip deleted token
                        if udn['upos']=='PRON' and (udn['feats'] or {}).get('Poss')=='Yes': # note that PRP$/WP$ doesn't include 'mine' etc.
                            assert leaf.lemma=={'my': 'I', 'mine': 'I', 'your': 'you', 'yours': 'you',
                                                'his': 'he', 'her': 'she', 'hers': 'she', 'its': 'it',
                                                'our': 'we', 'ours': 'we', 'their': 'they', 'theirs': 'they'}[udn['lemma']],(leaf.lemma,udn['lemma'],cgel_tree.sentid)
                        elif udn['upos']=='PRON' and (udn['feats'] or {}).get('Reflex')=='Yes':
                            assert leaf.lemma=={'myself': 'I', 'ourselves': 'we',
                                                'yourself': 'you', 'yourselves': 'you',
                                                'himself': 'him', 'herself': 'her', 'itself': 'it',
                                                'themselves': 'they'}[udn['lemma']],(leaf.lemma,udn['lemma'],cgel_tree.sentid)
                        elif not (udn['lemma']==leaf.lemma or (cgeltagged,udtagged) in DIVERGENCES):
                            if udn['lemma'].lower()==leaf.lemma.lower():
                                print('Lemma capitalization divergence',cgeltagged,udtagged)
                            else:
                                assert False,(cgeltagged,leaf.correct,udtagged,cgel_tree.sent)
                    break
                assert udn['upos']!='PUNCT' or (cgeltagged,udtagged) in DIVERGENCES,(cgeltagged,udtagged)
                if not (leaf.lemma=='get' or (udn['upos']=='AUX')==(leaf.constituent=='V_aux')):
                    print('POS mismatch (could be due to existential):', leaf.text, leaf.constituent, cgel_tree.sent)

            for p in leaf.postpunct:
                if hold_word2:
                    udn = hold_word2
                    hold_word2 = None
                else:
                    udn = next(udI)
                assert udn['form']==p and udn['upos']=='PUNCT',(p,udn)
