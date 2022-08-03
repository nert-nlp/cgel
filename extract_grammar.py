"""
Create a grammar with rules attested in the corpus.

TODO: Options control refinement of nonterminals. E.g. clause types, marked coordinate categories

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
        'heads-only': In the RHS of a rule only display items in the Head function.
        'ignore-supp': In the RHS of a rule, omit items in the Supplement function.
        'group-cats': In the RHS of a rule, group together all constituent categories under each function.
    """
    assert tree.tokens[i] is node
    children = [(c,tree.tokens[c]) for c in tree.children[i]]
    if children:
        rhsCondition = lambda x: ('Head' in x.deprel or 'heads-only' not in opts) and (x.deprel!='Supplement' or 'ignore-supp' not in opts)
        rhs = ' '.join(f'{ch.deprel}:{ch.constituent}' for ch in list(zip(*children))[1] if rhsCondition(ch))
        if 'group-cats' in opts:
            fullrhs = rhs
            rhs = ' '.join(f'{ch.deprel}:*' for ch in list(zip(*children))[1] if rhsCondition(ch))
        rule = f'{node.constituent} -> {rhs}'
        if not select_rules or rule in select_rules:
            counts[rule] += 1
            if len(examples[rule])<5:
                ex = tree.draw_rec(i, 0)
                if ex.count('\n')<5:
                    ex += '\n' + tree.sent
                examples[rule].add(ex)
        for c,ch in children:
            count_rules(c, ch, tree, counts, examples, select_rules, opts)

if __name__=='__main__':
    rules = Counter()
    examples = defaultdict(set)

    SELECTED_RULES = {  # heads-only rules
                #'Clause -> ',
                'Clause -> Head:V',
                'DP -> Head:Flat',
                'NP -> Det-Head:DP',
                'NP -> Det-Head:DP Head:GAP',
                'NP -> Det-Head:NP Head:Nom',
                'NP -> Head-Prenucleus:NP Head:Nom',
                'Nom -> Head:NP',
                'VP -> Head:V Head:Coordination'}
    # SELECTED_RULES = { # 'PP -> Head:P PredComp:NP', # as-PPs
    #     #'PP -> Comp:NP Head:PP', # NPN construction: 'back to back'
    #     'PP -> Head:P Mod:PP Mod:PP'}
    #SELECTED_RULES |= {'VP -> Head:VP Mod:DP','VP -> Head:V_aux Comp:NP'}
    # SELECTED_RULES = {'NP -> Head-Prenucleus:NP Head:Nom', 'NP -> Head:Nom Mod:Clause_rel',
    #     'NP -> Head:Nom Supplement:VP', 'NP -> Mod:AdjP Head:NP', 'NP -> Mod:AdjP Head:Nom'}
    #
    SELECTED_RULES = {'VP -> Head:* Mod:* Comp:*','VP -> Head:* Comp:* Mod:*','VP -> Head:* Obj:* Mod:*',
        'VP -> Head:* PredComp:* Mod:*', 'VP -> Mod:* Head:* Obj:*', 'VP -> Head:* Mod:* PredComp:*', 'VP -> Head:* Subj:*',
        'VP -> Head:* DisplacedSubj:*', 'VP -> Mod:* Head:* Comp:*',
        'VP -> Head:* DisplacedSubj:* Mod:*', 'VP -> Marker:* Head:* Mod:*'}

    # TODO: examine Clause -> * rules

    #SELECTED_RULES |= {'AdjP -> Head:Adj Mod:PP'}
    #SELECTED_RULES = set()
    with open('datasets/twitter.cgel') as f, open('datasets/ewt.cgel') as f2:
        i = 0
        for tree in cgel.trees(chain(f,f2)):
            s = tree.draw()
            r = tree.get_root()
            root = tree.tokens[r]
            rule = f'ROOT -> {root.constituent}'
            rules[rule] += 1
            count_rules(r, root, tree, rules, examples,
                select_rules=SELECTED_RULES,
                opts={'heads-only', 'group-cats'} and {'ignore-supp'} and {'group-cats','ignore-supp'})

    for k,v in sorted(rules.items(), key=lambda x: (x[0].split()[0], -x[1], x[0].split()[1:])):
        print(f'{v:3}', k)
        if 'print examples' and SELECTED_RULES:
            for ex in examples[k]:
                print(ex)
            print()

    for rule in SELECTED_RULES:
        if rules[rule]==0:
            print(f'Unattested: {rule}')
