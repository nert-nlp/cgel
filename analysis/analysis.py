import conllu
import sys
sys.path.append('../')
import cgel
from collections import Counter
from math import log
from difflib import get_close_matches

# helper functions for calculating entropy + conditional entropy
def H(c):
    res = 0
    for _, freq in c.items():
        res -= freq / tot * log(freq / tot, 2)
    return res

def cond_H(count, given, pos):
    return -(count / tot) * log((count / tot) / (given[pos] / tot), 2)

# read UD trees
with open('../datasets/twitter_ud.conllu') as f, open('../datasets/ewt_ud.conllu') as f2:
    ud_data = conllu.parse(f.read() + f2.read())

# parse CGEL trees + output conllu-style versions of them
trees = []
with open('../datasets/twitter_cgel.txt') as f, open('../datasets/ewt_cgel.txt') as f2, open('cgel.conllu', 'w') as fout:
    a = ''.join([x for x in f.readlines() + f2.readlines() if x[0] in [' ', '(']])
    for tree in cgel.parse(a):
        trees.append(conllu.parse(tree.to_conllu())[0])
        fout.write(trees[-1].serialize())

# go through each tree for analysis
# currently: POS tag comparisons (entropy), agreement in heads
cgel, ud, penn = Counter(), Counter(), Counter()
cgel_ud, ud_penn, penn_cgel = Counter(), Counter(), Counter()
match_ud, all_ud = Counter(), Counter()

tot = 0
leave = False
actual_tot = 0
agree_head = 0

for ud_tree, cgel_tree in zip(ud_data, trees):

    # count # of tokens total, ignoring multiword spans
    for tok in ud_tree:
        if tok['lemma'] != '_': actual_tot += 1

    # POS tags + find alignments
    leave = False
    j = 0
    alignment = {}
    mapping_cgel = {}
    mapping_ud = {}
    for i, cgel_tok in enumerate(cgel_tree):

        # align tokens
        while (not get_close_matches(cgel_tok['form'].lower(), [ud_tree[j]['form'].lower()])) or ud_tree[j]['upos'] == '_':
            j += 1
            if j == len(ud_tree) - 1:
                leave = True
                break
        if leave:
            break
        alignment[i] = j
        mapping_cgel[cgel_tree[i]['id']] = i
        mapping_ud[ud_tree[j]['id']] = j

        ud_tok = ud_tree[j]
        ud_pos = ud_tok['upos']
        penn_pos = ud_tok['xpos']
        cgel_pos = cgel_tok['upos']

        ud[ud_pos] += 1
        penn[penn_pos] += 1
        cgel[cgel_pos] += 1
        cgel_ud[(cgel_pos, ud_pos)] += 1
        ud_penn[(ud_pos, penn_pos)] += 1
        penn_cgel[(penn_pos, cgel_pos)] += 1

        tot += 1
        j += 1

    # head agreement
    for i, j in alignment.items():

        # get heads of both UD and CGEL tokens and make sure they exist
        cgel_head = mapping_cgel.get(cgel_tree[i]['head'], None)
        ud_head = mapping_ud.get(ud_tree[j]['head'], None)

        if cgel_head and ud_head:
            all_ud[ud_tree[j]['deprel']] += 1

            # count cases with alignments of heads
            if alignment[cgel_head] == ud_head:
                match_ud[ud_tree[j]['deprel']] += 1
                agree_head += 1
            # elif ud_tree[j]['deprel'] == 'obj':
            #     print(cgel_tree, ud_tree)
            #     print('\t', cgel_tree[i], ud_tree[j])
            #     print('\t', cgel_tree[cgel_head], ud_tree[ud_head])
            #     input()

cond_cgel_ud = 0
res = Counter()
print('H(CGEL | UD)')
for (cgel_pos, ud_pos), count in cgel_ud.items():
    x = cond_H(count, ud, ud_pos)
    cond_cgel_ud += x
    if x != 0:
        res[(cgel_pos, ud_pos)] = x
res2 = Counter()
for x, y in res.most_common():
    res2[x[0]] += y
    print(x, f'{y:.4}')
print()
for x, y in res2.most_common():
    print(x, f'{y:.4}')

cond_cgel_penn = 0
res = Counter()
print('H(CGEL | PTB)')
for (penn_pos, cgel_pos), count in penn_cgel.items():
    x = cond_H(count, penn, penn_pos)
    cond_cgel_penn += x
    if x != 0:
        res[(cgel_pos, penn_pos)] = x
res2 = Counter()
for x, y in res.most_common():
    res2[x[0]] += y
    print(x, f'{y:.4}')
print()
for x, y in res2.most_common():
    print(x, f'{y:.4}')

cond_ud_penn = 0
res = Counter()
print('H(UD | PTB)')
for (ud_pos, penn_pos), count in ud_penn.items():
    x = cond_H(count, penn, penn_pos)
    cond_ud_penn += x
    if x != 0:
        res[(ud_pos, penn_pos)] = x
res2 = Counter()
for x, y in res.most_common():
    res2[x[0]] += y
    print(x, f'{y:.4}')
print()
for x, y in res2.most_common():
    print(x, f'{y:.4}')

print(cgel)
print(len(trees))
print('Alignment:', actual_tot, tot, f'{tot / actual_tot:0.1%}')
print(f'H(CGEL) = {H(cgel)} ({len(cgel)})')
print(f'H(UD)   = {H(ud)} ({len(ud)})')
print(f'H(Penn) = {H(penn)} ({len(penn)})')
print(f'H(CGEL | UD)   = {cond_cgel_ud}')
print(f'H(CGEL | Penn) = {cond_cgel_penn}')
print(f'H(UD | Penn) = {cond_ud_penn}')

print()
print('DEPRELS')
print('Same head:', f'{agree_head / tot:0.1%}')
head_pairs = Counter()
for i in all_ud:
    head_pairs[i] = match_ud[i] / all_ud[i]
for x, y in head_pairs.most_common():
    print(x, f'{y:0.1%}', f'({all_ud[x]})')
