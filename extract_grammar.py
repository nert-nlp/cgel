"""
Create a grammar with rules attested in the corpus.
Options control refinement of nonterminals.

@author: Nathan Schneider (@nschneid)
@since: 2022-07-30
"""

import re, sys
from collections import Counter, defaultdict
from itertools import chain
import cgel

def count_rules(i, node, tree, counts, examples, select_rules=set(), opts=set()):
    """
    Options to provide in `opts`:
        'heads-only': In the RHS of a rule only display items in the Head function
    """
    assert tree.tokens[i] is node
    children = [(c,tree.tokens[c]) for c in tree.children[i]]
    if children:
        rhs = ' '.join(f'{ch.deprel}:{ch.constituent}' for ch in list(zip(*children))[1] if 'Head' in ch.deprel or 'heads-only' not in opts)
        rule = f'{node.constituent} -> {rhs}'
        if not select_rules or rule in select_rules:
            counts[rule] += 1
            if len(examples[rule])<5:
                yld = tree.draw_rec(i, 0)
                examples[rule].add(yld)
        for c,ch in children:
            count_rules(c, ch, tree, counts, examples, select_rules, opts)

if __name__=='__main__':
    rules = Counter()
    examples = defaultdict(set)
    with open('datasets/twitter.cgel') as f, open('datasets/ewt.cgel') as f2:
        i = 0
        for tree in cgel.trees(chain(f,f2)):
            s = tree.draw()
            r = tree.get_root()
            root = tree.tokens[r]
            rule = f'ROOT -> {root.constituent}'
            rules[rule] += 1
            count_rules(r, root, tree, rules, examples,
                select_rules={'AdvP -> Head:P',
                            #'Clause -> ',
                            'Clause -> Head:V',
                            'DP -> Head:Flat',
                            'DP -> Head:N_pro',
                            'NP -> ',
                            'NP -> Head:GAP',
                            'NP -> Head:N',
                            'NP -> Head:N_pro',
                            'NP -> Head:Nom Head:VP',
                            'NP -> Head:VP'} and set(),
                opts={'heads-only'})

    for k,v in sorted(rules.items(), key=lambda x: (x[0].split()[0], -x[1], x[0].split()[1:])):
        print(f'{v:3}', k)
        # for ex in examples[k]:
        #     print(ex)
        # print()
