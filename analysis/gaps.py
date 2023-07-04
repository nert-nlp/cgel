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
Compare CGEL gaps to PTB empty categories on EWT data.
"""

with open('../datasets/ewt.conllu') as f2:
    ud_trees = conllu.parse(f2.read())

cgel_trees = []
with open('../datasets/twitter.cgel') as f, open('../datasets/ewt.cgel') as f2:
    for tree in cgel.trees(f2):
        cgel_trees.append(tree)

def ud_tok_scanner(ud_tree):
    for node in ud_tree:
        if isinstance(node['id'], int): # skip token ranges
            yield node

def penn_tok_scanner(tree, empty=False):
    for x in tree.strip().splitlines():
        if empty or '-NONE-' not in x:
            t = x.strip().split()[-1]
            t = t.replace('-LRB-','(').replace('-RRB-',')').replace('-LSB-','[').replace('-RSB-',']')
            yield t


"""Example:
newsgroup-groups.google.com_eHolistic_2dd76f31ceb6bfe8_ENG_20050513_224200-0008

( (S (SBAR-NOM-SBJ (WHNP-9 (WP What)) (S (NP-SBJ-1 (PRP we)) (VP (VBP are) (VP (VBG trying) (S (NP-SBJ-1 (-NONE- *PRO*))
  (VP (TO to) (VP (VB do) (NP-9 (-NONE- *T*)))))))))
  (VP (VBZ is) (S-PRD (NP-SBJ (-NONE- *PRO*)) (VP (VB solicit) (NP (NP (NNS votes)) (PP (IN for) (NP (DT the) (NN band))))
  (, ,) (PP-PRP (IN in) (NP (NN order) (S (NP-SBJ (-NONE- *PRO*)) (VP (TO to) (VP (VB put) (NP (PRP them))
  (PP-CLR (IN in) (NP (JJ first) (NN place))))))))))) (. .)) )

What_1 we_2 are_3 trying_4 *PRO*_4/5 to_5 do_6 *T*_6/7 is_7 *PRO*_7/8 solicit_8 votes_9 for_10 the_11 band_12 ,_13
in_14 order_15 *PRO*_15/16 to_16 put_17 them in first place .

Penn Gap locations: 4/5 6/7 7/8 15/16
Omitting *PRO*: 6/7
"""

gaps = set()
gaptypes = set()
ud_treesI = iter(ud_trees)
TIME_TO_BREAK = object()
while True:
    ud_tree = next(ud_treesI, TIME_TO_BREAK)
    if ud_tree is TIME_TO_BREAK:
        break
    sentid = ud_tree.metadata['sent_id']
    genre, docid, sentnum = sentid.split('-')
    assert genre in ('answers','email','newsgroup','reviews','weblog')
    sentnum = int(sentnum)
    with open(f'ewtdata/{genre}/penntree/{docid}.xml.tree') as pennF:
        for i,ln in zip(range(sentnum), pennF):
            otree = ln.strip()

    s = ud_tree.metadata['text']




    # Check that Penn overt tokens are aligned to UD tokens
    tree = re.sub(r'[)]+', '\n', otree)
    penntoks = list(penn_tok_scanner(tree))
    udtoks = [x['form'] for x in ud_tok_scanner(ud_tree)]
    if len(udtoks)<len(penntoks):
        assert udtoks[:4]==penntoks[:4]==['Billing', 'takes', '15', 'minutes']
        # Sentence that was split into 2 sentences in EWT/CGEL but not PTB
        # Here the sentence boundaries shouldn't matter as we are just comparing the linear gap positions
        ud_tree2 = next(ud_treesI)
        sentid2 = ud_tree.metadata['sent_id']
        udtoks2 = [x['form'] for x in ud_tok_scanner(ud_tree2)]
        udtoks += udtoks2
    assert len(penntoks)==len(udtoks),(penntoks,udtoks)
    assert penntoks==udtoks or 'n’t' in udtoks or 'companie$' in udtoks,list(zip_longest(penntoks,udtoks))

    pennterminals = list(penn_tok_scanner(tree,empty=True))


    # Having identified sentences of interest, print their trees
    # if sentid in dict([('newsgroup-groups.google.com_GayMarriage_0ccbb50b41a5830b_ENG_20050321_181500-0039', '16/17'), ('newsgroup-groups.google.com_GayMarriage_0ccbb50b41a5830b_ENG_20050321_181500-0039', '13/14')]):
    #     print(sentid)
    #     print(' '.join(pennterminals))
    #     print(otree)
    #     print()

    termsI = iter(pennterminals)
    term = None
    lastGapNotPRO = None
    for i,tok in enumerate(penntoks, start=1):
        term = next(termsI)
        while term!=tok:    # iterate until we are past the gap
            gaptypes.add(term)
            if term in ('*T*','*RNR*',) or True:    # without `or True`, filter to just these PTB gap types
                lastGapNotPRO = term
            term = next(termsI)
            if lastGapNotPRO:
                gapij = f'{i-1}/{i}'
                gaps.add((sentid,gapij))
                lastGapNotPRO = None

print('Done with',len(ud_trees),'trees')

#assert False,gaptypes

# Gap locations are indexed by the consecutive UD token offsets they are between
# N.B. there can be multiple gaps at the same location, in different tree positions

print(gaps)

# Obtained by running align_tokens.py
cgel_gaps_old = {('newsgroup-groups.google.com_herpesnation_c74170a0fcfdc880_ENG_20051125_075200-0024', '2/3'), ('newsgroup-groups.google.com_eHolistic_2dd76f31ceb6bfe8_ENG_20050513_224200-0022', '20/21'), ('newsgroup-groups.google.com_eHolistic_2dd76f31ceb6bfe8_ENG_20050513_224200-0008', '6/7'), ('weblog-blogspot.com_rigorousintuition_20060511134300_ENG_20060511_134300-0070', '19/20'), ('reviews-101398-0005', '12/13'), ('answers-20111106153454AAgT9Df_ans-0016', '18/19'), ('newsgroup-groups.google.com_civicamerican_22c54c292026bfd2_ENG_20060128_072400-0019', '12/13'), ('reviews-180886-0004', '9/10'), ('newsgroup-groups.google.com_alt.animals_0084bdc731bfc8d8_ENG_20040905_212000-0059', '7/8'), ('reviews-008585-0004', '4/5'), ('newsgroup-groups.google.com_alt.animals_0084bdc731bfc8d8_ENG_20040905_212000-0118', '9/10'), ('reviews-275919-0010', '20/21'), ('reviews-180886-0004', '19/20'), ('newsgroup-groups.google.com_humanities.lit.authors.shakespeare_0018a7697318f71f_ENG_20031006_163200-0092', '12/13'), ('newsgroup-groups.google.com_humanities.lit.authors.shakespeare_0018a7697318f71f_ENG_20031006_163200-0092', '3/4'), ('answers-20111106153454AAgT9Df_ans-0016', '15/16'), ('newsgroup-groups.google.com_GayMarriage_0ccbb50b41a5830b_ENG_20050321_181500-0039', '13/14'), ('weblog-blogspot.com_alaindewitt_20040929103700_ENG_20040929_103700-0050', '14/15'), ('email-enronsent13_01-0092', '7/8'), ('email-enronsent35_01-0010', '3/4'), ('newsgroup-groups.google.com_alt.animals_434fe80fb3577e8e_ENG_20031011_200300-0039', '23/24'), ('reviews-391012-0005', '9/10'), ('reviews-042012-0002', '17/18'), ('newsgroup-groups.google.com_alt.animals_0084bdc731bfc8d8_ENG_20040905_212000-0012', '23/24'), ('weblog-blogspot.com_alaindewitt_20040929103700_ENG_20040929_103700-0050', '8/9'), ('newsgroup-groups.google.com_civicamerican_22c54c292026bfd2_ENG_20060128_072400-0019', '17/18'), ('weblog-blogspot.com_alaindewitt_20040929103700_ENG_20040929_103700-0050', '6/7'), ('newsgroup-groups.google.com_eHolistic_2dd76f31ceb6bfe8_ENG_20050513_224200-0022', '7/8'), ('answers-20111108101850AAhNuvz_ans-0003', '6/7'), ('answers-20111108105629AAiZUDY_ans-0008', '6/7'), ('answers-20111108105400AASqPIh_ans-0007', '11/12'), ('answers-20111106153454AAgT9Df_ans-0016', '16/17'), ('answers-20111108111010AASEk0S_ans-0008', '20/21'), ('newsgroup-groups.google.com_INTPunderground_b2c62e87877e4a22_ENG_20050906_165900-0074', '13/14'), ('weblog-blogspot.com_rigorousintuition_20060511134300_ENG_20060511_134300-0070', '14/15'), ('newsgroup-groups.google.com_GayMarriage_0ccbb50b41a5830b_ENG_20050321_181500-0039', '16/17'), ('email-enronsent13_01-0092', '8/9'), ('newsgroup-groups.google.com_alt.animals_0084bdc731bfc8d8_ENG_20040905_212000-0152', '7/8'), ('newsgroup-groups.google.com_civicamerican_22c54c292026bfd2_ENG_20060128_072400-0019', '25/26'), ('email-enronsent15_01-0005', '13/14')}

cgel_gaps = {('newsgroup-groups.google.com_alt.animals_0084bdc731bfc8d8_ENG_20040905_212000-0118', '9/10'), ('newsgroup-groups.google.com_alt.animals_434fe80fb3577e8e_ENG_20031011_200300-0039', '23/24'), ('answers-20111106153454AAgT9Df_ans-0016', '18/19'),
# ('reviews-275919-0011', '5/6'), ('reviews-275919-0011', '7/8'), -- split from previous sent. instead:
('reviews-275919-0010', '18/19'), ('reviews-275919-0010', '20/21'),
('answers-20111108105400AASqPIh_ans-0007', '11/12'), ('newsgroup-groups.google.com_GayMarriage_0ccbb50b41a5830b_ENG_20050321_181500-0039', '13/14'), ('newsgroup-groups.google.com_eHolistic_2dd76f31ceb6bfe8_ENG_20050513_224200-0022', '7/8'), ('email-enronsent13_01-0092', '7/8'), ('email-enronsent35_01-0010', '3/4'), ('weblog-blogspot.com_alaindewitt_20040929103700_ENG_20040929_103700-0050', '6/7'), ('newsgroup-groups.google.com_INTPunderground_b2c62e87877e4a22_ENG_20050906_165900-0074', '13/14'), ('newsgroup-groups.google.com_GayMarriage_0ccbb50b41a5830b_ENG_20050321_181500-0039', '16/17'), ('answers-20111108111010AASEk0S_ans-0008', '20/21'), ('newsgroup-groups.google.com_eHolistic_2dd76f31ceb6bfe8_ENG_20050513_224200-0008', '6/7'), ('reviews-180886-0004', '9/10'), ('answers-20111106153454AAgT9Df_ans-0016', '15/16'), ('reviews-346960-0006', '8/9'), ('weblog-blogspot.com_rigorousintuition_20060511134300_ENG_20060511_134300-0070', '19/20'), ('newsgroup-groups.google.com_civicamerican_22c54c292026bfd2_ENG_20060128_072400-0019', '25/26'), ('newsgroup-groups.google.com_alt.animals_0084bdc731bfc8d8_ENG_20040905_212000-0152', '7/8'), ('newsgroup-groups.google.com_civicamerican_22c54c292026bfd2_ENG_20060128_072400-0019', '17/18'), ('newsgroup-groups.google.com_civicamerican_22c54c292026bfd2_ENG_20060128_072400-0019', '12/13'), ('newsgroup-groups.google.com_alt.animals_0084bdc731bfc8d8_ENG_20040905_212000-0012', '23/24'), ('answers-20111108101850AAhNuvz_ans-0003', '6/7'), ('newsgroup-groups.google.com_misc.consumers_a534e32067078b08_ENG_20060116_030800-0099', '3/4'),
('newsgroup-groups.google.com_eHolistic_2dd76f31ceb6bfe8_ENG_20050513_224200-0022', '20/21'), ('weblog-blogspot.com_alaindewitt_20040929103700_ENG_20040929_103700-0050', '8/9'), ('reviews-101398-0005', '12/13'), ('email-enronsent13_01-0092', '8/9'), ('weblog-blogspot.com_dakbangla_20041119231111_ENG_20041119_231111-0033', '5/6'), ('newsgroup-groups.google.com_alt.animals_0084bdc731bfc8d8_ENG_20040905_212000-0059', '7/8'), ('newsgroup-groups.google.com_herpesnation_c74170a0fcfdc880_ENG_20051125_075200-0024', '2/3'), ('newsgroup-groups.google.com_humanities.lit.authors.shakespeare_0018a7697318f71f_ENG_20031006_163200-0092', '3/4'), ('newsgroup-groups.google.com_humanities.lit.authors.shakespeare_0018a7697318f71f_ENG_20031006_163200-0092', '12/13'), ('weblog-blogspot.com_rigorousintuition_20060511134300_ENG_20060511_134300-0070', '14/15'), ('newsgroup-groups.google.com_misc.consumers_a534e32067078b08_ENG_20060116_030800-0066', '4/5'), ('weblog-blogspot.com_alaindewitt_20040929103700_ENG_20040929_103700-0050', '14/15'), ('answers-20111106153454AAgT9Df_ans-0016', '16/17'), ('reviews-042012-0002', '17/18'), ('reviews-008585-0004', '4/5'), ('answers-20111108105629AAiZUDY_ans-0008', '6/7'), ('reviews-391012-0005', '9/10'), ('reviews-180886-0004', '19/20'), ('newsgroup-groups.google.com_INTPunderground_b2c62e87877e4a22_ENG_20050906_165900-0074', '24/25'), ('email-enronsent15_01-0005', '13/14')}

print('nPTBGapLocations', len(gaps), 'nCGELGapLocations', len(cgel_gaps))

print('Intersection', len(gaps & cgel_gaps))

print(gaps & cgel_gaps)

print()

print(gaps - cgel_gaps)

print()

print(cgel_gaps - gaps)
