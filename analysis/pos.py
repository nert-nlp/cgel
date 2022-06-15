import conllu
import sys
sys.path.append('../')
import cgel
from collections import Counter
from math import log
from difflib import get_close_matches

# with open('../datasets/twitter_parsed/sentences_fixed.conllu') as f:
with open('../datasets/cgel_from_ud/ud_train.conllu') as f:
    ud_data = conllu.parse(f.read())

trees = []
# with open('../datasets/twitter_parsed/parsed.txt') as f:
with open('../datasets/cgel_from_ud/training_set.txt') as f:
    for tree in cgel.parse(''.join([x for x in f.readlines() if x[0] in [' ', '(']])):
        trees.append(conllu.parse(tree.to_conllu())[0])

cgel, ud, penn = Counter(), Counter(), Counter()
cgel_ud, ud_penn, penn_cgel = Counter(), Counter(), Counter()

tot = 0
leave = False
for ud_tree, cgel_tree in zip(ud_data, trees):
    leave = False
    j = 0
    for cgel_tok in cgel_tree:
        print(cgel_tok)
        while not get_close_matches(cgel_tok['form'].lower(), [ud_tree[j]['form'].lower()]):
            # print(cgel_tok['form'], [ud_tree[j]['form']])
            j += 1
            if j == len(ud_tree) - 1:
                input()
                leave = True
                break
        if leave:
            break
        
        ud_tok = ud_tree[j]
        print(ud_tok, cgel_tok)
        ud_pos = ud_tok['upos']
        penn_pos = ud_tok['xpos']
        cgel_pos = cgel_tok['upos']
        if cgel_pos == 'D' and penn_pos == 'RB':
            print(cgel_tok, ud_tok)
            input()
        
        ud[ud_pos] += 1
        penn[penn_pos] += 1
        cgel[cgel_pos] += 1
        cgel_ud[(cgel_pos, ud_pos)] += 1
        ud_penn[(ud_pos, penn_pos)] += 1
        penn_cgel[(penn_pos, cgel_pos)] += 1
        tot += 1

def H(c):
    res = 0
    for _, freq in c.items():
        res -= freq / tot * log(freq / tot, 2)
    return res

def cond_H(count, given, pos):
    return -(count / tot) * log((count / tot) / (given[pos] / tot), 2)

cond_cgel_ud = 0
res = Counter()
for (cgel_pos, ud_pos), count in cgel_ud.items():
    x = cond_H(count, ud, ud_pos)
    cond_cgel_ud += x
    if x != 0:
        res[(cgel_pos, ud_pos)] = x
for x, y in res.most_common():
    print(x, y)
print()

cond_cgel_penn = 0
res = Counter()
for (penn_pos, cgel_pos), count in penn_cgel.items():
    x = cond_H(count, penn, penn_pos)
    cond_cgel_penn += x
    if x != 0:
        res[(cgel_pos, penn_pos)] = x
for x, y in res.most_common():
    print(x, y)

print(f'H(CGEL) = {H(cgel)} ({len(cgel)})')
print(f'H(UD)   = {H(ud)} ({len(ud)})')
print(f'H(Penn) = {H(penn)} ({len(penn)})')
print(f'H(CGEL | UD)   = {cond_cgel_ud}')
print(f'H(CGEL | Penn) = {cond_cgel_penn}')