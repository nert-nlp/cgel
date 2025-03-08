import conllu
import sys
sys.path.append('../')
import glob
import pandas as pd
import cgel
from collections import Counter, defaultdict
from math import log
from difflib import get_close_matches
from itertools import zip_longest, chain
import argparse

"""
Report stats on CGEL only (without aligning to UD): summary stats
and/or detailed breakdown by categories and functions.
Can print output as Markdown, code, or tex (`-h` to see options).
"""

all_files = [
    '../datasets/twitter.cgel',
    '../datasets/ewt.cgel',
    '../datasets/ewt-test_pilot5.cgel',
    '../datasets/ewt-test_iaa50.cgel',
    '../datasets/trial/ewt-trial.cgel',
    '../datasets/trial/twitter-etc-trial.cgel',
] + glob.glob('../datasets/oneoff/*.cgel')

def map_mult(s, olds, new):
    return new if any(o==s for o in olds) else s

def overview(trees: list[cgel.Tree]):
    print("\n## Overview\n")
    print("- Trees:", len(trees))
    print("- Nodes:", sum(t.size for t in trees))
    print("- Lexical Nodes:", (lexNodes := sum(len(t.terminals(gaps=False)) for t in trees)), f"({lexNodes/len(trees):.1f}/tree)")
    print("- Lexical Insertions (nodes where surface string is empty due to typo):", sum(1 for t in trees for term in t.terminals(gaps=False) if not term.text))
    print("- Gaps:", sum(len(t.terminals(gaps=True)) for t in trees)-lexNodes)
    print("- Punctuation Tokens:", sum(len(term.prepunct)+len(term.postpunct) for t in trees for term in t.terminals(gaps=False)))
    #print("Length:", sum(t.length for t in trees) / len(trees))    # same as Lexical Nodes per Tree, apparently
    print(f"- Avg Tree Depth: {sum(t.depth for t in trees) / len(trees):.1f}")

def analyse_pos(trees: list[cgel.Tree], mode='code' or 'tex' or 'markdown'):
    cgels = Counter()
    lemmas = Counter()
    cats = Counter()
    fxns = Counter()
    catsbyfxn = defaultdict(Counter)    # for each function, what categories occur in that function?
    parcatsbyfxn = defaultdict(Counter) # for each function, what categories of parent does it have?
    high_valencies = Counter()
    poses_by_lemma = defaultdict(set)
    ambig_class = defaultdict(set)
    fxn_words = {'D': set(), 'N_pro': set(), 'V_aux': set(), 'P': set(), 'Sdr': set(), 'Coordinator': set()}

    # node properties: 'constituent' (POS or phrasal category), 'deprel' (grammatical function), 'head' (index), 'label' (coindexation variable), 'text' (terminals only)
    for cgel_tree in trees:
        for n,node in cgel_tree.tokens.items():
            if not node.deprel:
                assert node.head==-1
                fxns['(root)'] += 1
            else:
                fxns[node.deprel] += 1

            p, = [i for i in cgel_tree.children if n in cgel_tree.children[i]]
            parcat = cgel_tree.tokens[p].constituent if p>-1 else 'ROOT'
            if node.deprel and '+' not in parcat:
                parcatsbyfxn[parcat][node.deprel] += 1

            if node.text or node.correct:   # terminal
                cgel_pos = node.constituent
                cgels[cgel_pos] += 1
                lemma = node.lemma
                lemmas[lemma] += 1
                poses_by_lemma[lemma].add(cgel_pos)
                if lemma in ('be',) and cgel_pos=='P':
                    assert False,node
                if cgel_pos not in ('V','N','Adj','Adv','Int'):
                    if lemma is not None:   # will be None for deleted words
                        fxn_words[cgel_pos].add(lemma)
            else:  # nonterminal
                if node.constituent in ('N','V','Adj','Adv','D','P','Coordinator','Int','N_pro','Sbr','V_aux'):
                    # "nonterminal" bears a lexical category
                    # most of these are due to preprocessing errors. a couple are legitimate lexical coordinations
                    if node.deprel=='Coordinate':
                        cats[node.constituent+'@coord'] += 1
                    elif cgel_tree.children[n] and cgel_tree.tokens[cgel_tree.children[n][0]].deprel=='Flat':
                        cats[node.constituent+'@flat'] += 1
                    else:
                        print('weird',node.deprel,node.constituent,cgel_tree.sentence())
                        continue

                else:
                    cats[node.constituent] += 1
                    if '+' not in node.constituent:
                        catsbyfxn[node.constituent][node.deprel or '(root)'] += 1
                    if node.constituent!='Coordination':
                        ch_nonsupp = [cgel_tree.tokens[c] for c in cgel_tree.children[n] if cgel_tree.tokens[c].deprel not in ('Supplement','Vocative')]
                        if len(ch_nonsupp)>2:
                            valency = f'({node.constituent} ' + ' '.join(f':{ch.deprel} {ch.constituent}' for ch in ch_nonsupp) + ')'
                            high_valencies[valency] += 1


    TOP_72 = {'be': 120, 'the': 103, 'to': 83, 'and': 66, 'a': 63, 'of': 52, 'i': 52, 'that': 48, 'have': 41, 'in': 38,
        'it': 29, 'you': 25, 'for': 24, 'they': 22, 'we': 20, 'do': 18, 'on': 18, 'this': 18, 'my': 16, 'at': 15, 'with': 14,
        'so': 14, 'as': 14, 'your': 13, 'not': 13, 'will': 12, 'get': 12, 'he': 12, 'just': 11, 'if': 11, 'can': 11, 'or': 11,
        'what': 10, 'all': 10, 'take': 10, 'but': 10, "'s": 9, 'who': 9, 'there': 9, 'time': 9, 'go': 8, 'would': 8, 'new': 8,
        'by': 8, 'an': 8, 'like': 8, 'person': 7, 'about': 7, 'more': 7, 'me': 7, 'from': 7, 'his': 7, 'out': 6, 'call': 6,
        'enough': 6, 'now': 6, 'their': 6, 'should': 6, 'could': 6, 'also': 6, 'any': 6, 'come': 6, 'our': 6, 'find': 5, 'how': 5,
        'want': 5, 'think': 5, 'very': 5, 'one': 5, 'first': 5, 'try': 5, 'him': 5}
    for lemma,poses in poses_by_lemma.items():
        if lemmas[lemma]>=5:
            ambig_class[frozenset(poses)].add(lemma)

    if mode!='tex':
        print('\n## POS categories\n')
        if mode=='code':
            print(cgels)
        elif mode=='markdown':
            df = pd.DataFrame.from_records(cgels.most_common(), columns=['POS','count'])
            print(df.to_markdown(index=False))

    #print(lemmas.most_common(70))

    print('\n## Lemmas occurring >=5 times, by categories the lemma appears in\n')
    if mode=='code':
        print(ambig_class)
    else:
        for k,v in ambig_class.items():
            print('- `{' + ', '.join(x for x in sorted(k)) + '}`: ', ' '.join(sorted(v)), sep='')

    print('\n## All lexemes of closed-class categories\n')
    if mode=='code':
        print(fxn_words)
    else:
        for k,v in fxn_words.items():
            if mode=='markdown':
                print(f'- `{k}`', ': ', ', '.join(sorted(v)), sep='')
            else:
                print(f'{k:>11}', ': ', ', '.join(sorted(v)), sep='')

    if mode!='tex':
        print('\n## Nonterminal categories\n')
        if mode=='code':
            print(cats)
        elif mode=='markdown':
            df = pd.DataFrame.from_records(cats.most_common(), columns=['category','count'])
            print(df.to_markdown(index=False))

        print('\n## Functions\n')
        if mode=='code':
            print(fxns)
        elif mode=='markdown':
            df = pd.DataFrame.from_records(fxns.most_common(), columns=['function','count'])
            print(df.to_markdown(index=False))

    # tags, cats, fxns formatted for LaTeX table
    if mode=='tex':
        nGAPs = cats['GAP']
        del cats['GAP']
        del fxns['(root)']
        for (p,pN),(c,cN),(f,fN) in zip_longest(cgels.most_common(), cats.most_common(), fxns.most_common(), fillvalue=('','')):
            p = p.replace("_",r"\_")
            c = c.replace("_",r"\_")
            f = f.replace("_",r"\_")
            print(rf'{pN:3} & {p:11} & {cN:4} & {c:20} & {fN:4} & {f} \\')
        print(nGAPs, r'& \textit{GAP}')

    print('\n## High Valencies (ternary+, omitting Supplements and Coordinations)\n')
    if mode=='code':
        print(fxns)
    else:
        df = pd.DataFrame.from_records(high_valencies.most_common(), columns=['valency','count'])
        print(df.to_markdown(index=False))

    print('\n## Nonlexical Categories by Function (excluding nonce categories)\n')
    if mode=='code':
        print(catsbyfxn)
    else:
        df = pd.DataFrame.from_records(catsbyfxn).fillna(0).astype(int)
        # sort columns by total
        s = df.sum()
        df = df[s.sort_values(ascending=False).index]
        # sort rows by total
        df = (df.assign(sum=df.sum(axis=1))  # Add temporary 'sum' column to sum rows.
               .sort_values(by='sum', ascending=False)  # Sort by row sum descending order.
               .iloc[:, :-1])  # Remove temporary `sum` column.
        print(df.to_markdown(index=True).replace(' 0 |', '   |'))

    print('\n## Parent Categories by Function (excluding nonce categories and root)\n')
    if mode=='code':
        print(parcatsbyfxn)
    else:
        df = pd.DataFrame.from_records(parcatsbyfxn).fillna(0).astype(int)
        # sort columns by total
        s = df.sum()
        df = df[s.sort_values(ascending=False).index]
        # sort rows by total
        df = (df.assign(sum=df.sum(axis=1))  # Add temporary 'sum' column to sum rows.
               .sort_values(by='sum', ascending=False)  # Sort by row sum descending order.
               .iloc[:, :-1])  # Remove temporary `sum` column.
        print(df.to_markdown(index=True).replace(' 0 |', '   |'))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', help='type of analysis', type=str, default='both', required=False)
    parser.add_argument('--mode', help='output format for POS analysis: code, markdown, or tex', type=str, default='markdown', required=False)
    parser.add_argument('files', help='files to analyse', type=str, nargs='*', default='all')
    args = parser.parse_args()

    #files = [all_files[args.file]] if args.file != "all" else list(all_files.values())
    files = all_files if args.files=='all' else args.files
    trees = []

    for cgelFP in files:
        with open(cgelFP, 'r') as f:
            try:
                for tree in cgel.trees(f):
                    trees.append(tree)
            except RuntimeError:
                print(f'No tree in {cgelFP}, ignoring', file=sys.stderr)

    print("# CGELBank Statistics\n")
    print(f'Analyzing {len(files)} files:\n')
    if args.mode=='code':
        print(files)
    else:
        for fp in files:
            if fp.startswith('../'):
                fp = fp[3:]
            if args.mode=='markdown':
                print(f'- [{fp}]({fp})')
            else:
                print(fp)

    if args.type == 'overview':
        overview(trees)
    elif args.type == 'pos':
        analyse_pos(trees, mode=args.mode)
    elif args.type == 'both':
        overview(trees)
        print()
        analyse_pos(trees, mode=args.mode)

if __name__ == "__main__":
    main()