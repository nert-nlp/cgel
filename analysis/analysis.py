import conllu
import sys
sys.path.append('../')
import cgel
from collections import Counter
from math import log
from difflib import get_close_matches

def H(c, tot):
    """entropy (bits)"""
    res = 0
    for _, freq in c.items():
        res -= freq / tot * log(freq / tot, 2)
    return res

def cond_H(count, given, pos, tot):
    """conditional entropy (bits)"""
    return -(count / tot) * log((count / tot) / (given[pos] / tot), 2)

def read_cgel(lines, fout=None):
    """read CGEL trees from the lines of a file"""
    trees = []
    to_parse = ''.join([x for x in lines if x[0] in [' ', '(']])
    for tree in cgel.parse(to_parse):
        trees.append(conllu.parse(tree.to_conllu())[0])
        if fout:
            fout.write(trees[-1].serialize())
    return trees

def analyse(ud_data, trees):
    """meat of the analysis"""

    # go through each tree for analysis
    # currently: POS tag comparisons (entropy), agreement in heads
    cgel, ud, penn = Counter(), Counter(), Counter()
    cgel_ud, ud_penn, penn_cgel = Counter(), Counter(), Counter()
    match_ud, all_ud = Counter(), Counter()

    tot = 0
    leave = False
    actual_tot = 0
    actual_tot_no_punct = 0
    agree_head = 0

    for ud_tree, cgel_tree in zip(ud_data, trees):

        # count # of tokens total, ignoring multiword spans
        for tok in ud_tree:
            if tok['lemma'] != '_':
                actual_tot += 1
                if tok['upos'] != 'PUNCT':
                    actual_tot_no_punct += 1

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
    print('H(CGEL | UD)\n' + '=' * 40)
    for (cgel_pos, ud_pos), count in cgel_ud.items():
        x = cond_H(count, ud, ud_pos, tot)
        cond_cgel_ud += x
        if x != 0:
            res[(cgel_pos, ud_pos)] = x
    res2 = Counter()
    for x, y in res.most_common():
        res2[x[0]] += y
        print(f'{str(x):<20} {y:.4f}')
    print()
    for x, y in res2.most_common():
        print(f'{x:<5} {y:.4f}')

    cond_cgel_penn = 0
    res = Counter()
    print('\nH(CGEL | PTB)\n' + '=' * 40)
    for (penn_pos, cgel_pos), count in penn_cgel.items():
        x = cond_H(count, penn, penn_pos, tot)
        cond_cgel_penn += x
        if x != 0:
            res[(cgel_pos, penn_pos)] = x
    res2 = Counter()
    for x, y in res.most_common():
        res2[x[0]] += y
        print(f'{str(x):<20} {y:.4f}')
    print()
    for x, y in res2.most_common():
        print(f'{x:<5} {y:.4f}')

    cond_ud_penn = 0
    res = Counter()
    print('\nH(UD | PTB)\n' + '=' * 40)
    for (ud_pos, penn_pos), count in ud_penn.items():
        x = cond_H(count, penn, penn_pos, tot)
        cond_ud_penn += x
        if x != 0:
            res[(ud_pos, penn_pos)] = x
    res2 = Counter()
    for x, y in res.most_common():
        res2[x[0]] += y
        print(f'{str(x):<20} {y:.4f}')
    print()
    for x, y in res2.most_common():
        print(f'{x:<5} {y:.4f}')

    print()
    print(cgel)
    print('Number of trees:', len(trees))
    print('Alignment:', actual_tot, tot, f'{tot / actual_tot:0.1%}')
    print('Alignment (-punct):', actual_tot_no_punct, tot, f'{tot / actual_tot_no_punct:0.1%}')
    print(f'H(CGEL)        = {H(cgel, tot):.2f} ({len(cgel)})')
    print(f'H(UD)          = {H(ud, tot):.2f} ({len(ud)})')
    print(f'H(Penn)        = {H(penn, tot):.2f} ({len(penn)})')
    print(f'H(CGEL | UD)   = {cond_cgel_ud}')
    print(f'H(CGEL | Penn) = {cond_cgel_penn}')
    print(f'H(UD | Penn)   = {cond_ud_penn}')

    print()
    print('DEPRELS (CGEL vs UD)')
    print('Same head:', f'{agree_head / tot:0.1%}')
    head_pairs = Counter()
    for i in all_ud:
        head_pairs[i] = match_ud[i] / all_ud[i]
    for x, y in head_pairs.most_common():
        print(f'{x:<20} {y:>6.1%} ({all_ud[x]})')

def main():
    # read UD trees
    with open('../datasets/twitter_ud.conllu') as f, open('../datasets/ewt_ud.conllu') as f2:
        twitter, ewt = f.read(), f2.read()
        twitter_ud = conllu.parse(twitter)
        ewt_ud = conllu.parse(ewt)
        all_ud = conllu.parse(twitter + ewt)

    # parse CGEL trees + output conllu-style versions of them
    with open('../datasets/twitter.cgel') as f, open('../datasets/ewt.cgel') as f2, open('cgel.conllu', 'w') as fout:
        twitter, ewt = f.readlines(), f2.readlines()
        twitter_trees = read_cgel(twitter)
        ewt_trees = read_cgel(ewt)
        all_trees = read_cgel(twitter + ewt, fout)

    # analyse(twitter_ud, twitter_trees)
    # analyse(ewt_ud, ewt_trees)
    analyse(all_ud, all_trees)

if __name__ == '__main__':
    main()