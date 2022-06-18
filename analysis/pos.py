import conllu
import sys
sys.path.append('../')
import cgel
from collections import Counter
from math import log
from difflib import get_close_matches

with open('../datasets/twitter_ud.conllu') as f, open('../datasets/ewt_ud.conllu') as f2:
    ud_data = conllu.parse(f2.read())

trees = []
with open('../datasets/twitter_cgel.txt') as f, open('../datasets/ewt_cgel.txt') as f2:
    a = ''.join([x for x in f2.readlines() if x[0] in [' ', '(']])
    for tree in cgel.parse(a):
        trees.append(conllu.parse(tree.to_conllu())[0])

cgel, ud, penn = Counter(), Counter(), Counter()
cgel_ud, ud_penn, penn_cgel = Counter(), Counter(), Counter()

tot = 0
leave = False
actual_tot = 0
for ud_tree, cgel_tree in zip(ud_data, trees):
    leave = False
    j = 0
    for tok in ud_tree:
        if tok['lemma'] != '_': actual_tot += 1
    for cgel_tok in cgel_tree:
        while (not get_close_matches(cgel_tok['form'].lower(), [ud_tree[j]['form'].lower()])) or ud_tree[j]['upos'] == '_':
            j += 1
            if j == len(ud_tree) - 1:
                # input()
                leave = True
                break
        if leave:
            break
        
        ud_tok = ud_tree[j]
        ud_pos = ud_tok['upos']
        penn_pos = ud_tok['xpos']
        cgel_pos = cgel_tok['upos']
        # if cgel_pos == 'N' and penn_pos == 'JJ':
        #     print(cgel_tok, ud_tok)
        #     input()
        
        ud[ud_pos] += 1
        penn[penn_pos] += 1
        cgel[cgel_pos] += 1
        cgel_ud[(cgel_pos, ud_pos)] += 1
        ud_penn[(ud_pos, penn_pos)] += 1
        penn_cgel[(penn_pos, cgel_pos)] += 1

        tot += 1
        j += 1

def H(c):
    res = 0
    for _, freq in c.items():
        res -= freq / tot * log(freq / tot, 2)
    return res

def cond_H(count, given, pos):
    return -(count / tot) * log((count / tot) / (given[pos] / tot), 2)

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

print(cgel)
print(len(trees))
print('Alignment:', actual_tot, tot, f'{tot / actual_tot:.1%}')
print(f'H(CGEL) = {H(cgel)} ({len(cgel)})')
print(f'H(UD)   = {H(ud)} ({len(ud)})')
print(f'H(Penn) = {H(penn)} ({len(penn)})')
print(f'H(CGEL | UD)   = {cond_cgel_ud}')
print(f'H(CGEL | Penn) = {cond_cgel_penn}')