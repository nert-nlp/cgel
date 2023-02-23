#!/usr/bin/env python3
"""
Given trees in the 6-column export format of the activedop annotation platform,
prints them in the .cgel format. (Note that these won't have proper sentence IDs,
punctuation, etc.)

Input trees are not separated by blank lines.
Excerpts from a tree in the activedop export format:

#BOS 1 %% JoeAnnotator [0, 0, 0, 0, 1, 0, 23, 18]
well	--	Int-Head	--	--	500
not	--	Adv-Head	--	--	501
much	--	D-Head	--	--	502
I	--	Npro-Head	--	--	503
...
#500	--	IntP-Supplement	--	--	523
#501	--	AdvP-Mod	--	--	502
#502	--	DP.y-DetHead	--	--	509
...
#521	--	Clause-Comp	--	--	522
#522	--	PP-Mod	--	--	523
#523	--	NP	--	--	0
#EOS 1

@author: Nathan Schneider (@nschneid)
@since: 2022-12-30
"""

import fileinput, sys
from collections import defaultdict

from cgel import Tree

def chunks(inF):
    chunk = None    # omit BOS and EOS lines
    for ln in inF:
        if not ln.strip():
            assert chunk is None
            continue
        if chunk is None:
            assert ln.startswith('#BOS ')
            chunk = ''
            continue
        elif ln.startswith('#EOS '):
            assert chunk
            assert '#500' in chunk  # first nonterminal
            terms = chunk[:chunk.rindex('#500')]
            nonterms = chunk[len(terms):]
            terms = terms.strip().splitlines()
            nonterms = nonterms.strip().splitlines()
            yield terms, nonterms
            chunk = None
        else:
            chunk += ln

def load(inF):
    """Given export data in the provided file, iteratively load each tree
    as a CGEL Tree object."""

    for terms,nonterms in chunks(inF=inF):
        tree = Tree()
        sent = []
        # start terminal indexing with 1, and use 500-based nonterminal indexing

        nodes = {}  # i -> (w, func, cat, i, head)
        children = defaultdict(list)    # head -> [i, ...]
        root = None

        # find the root. store its exported index and put it in the tree at 0
        for ln in nonterms:
            i, _, cat, _, _, head = ln.split('\t')
            if head=='0':
                assert root is None
                root = int(i[1:])
                nodes[0] = (None, None, cat, 0, -1)

        # internal nonterminals (not root or preterminals)
        for ln in nonterms:
            i, _, cat_func, _, _, head = ln.split('\t')
            assert i.startswith('#')
            i = int(i[1:])
            if i==root: continue
            assert cat_func.count('-')==1,(cat_func,' '.join(tln.split('\t')[0] for tln in terms))
            cat, func = cat_func.split('-')
            cat = cat.replace("Clauserel","Clause_rel").replace("Npro","N_pro").replace("Vaux","V_aux")
            if '.' in cat:
                cat, label = cat.split('.')
                cat = label + ' / ' + cat
            func = func.replace("DetHead","Det-Head").replace("ModHead","Mod-Head").replace("MarkerHead","Marker-Head").replace("HeadPrenucleus","Head-Prenucleus").replace("PCComp","PredComp/Comp")
            head = int(head)
            if head==root: head = 0
            nodes[i] = (None, func, cat, i, head)
            children[head].append(i)

        # terminals/preterminals
        for i,ln in enumerate(terms, start=1):
            w, _, cat_func, _, _, head = ln.split('\t')
            w = w.replace("++"," ")
            cat, func = cat_func.split('-')
            cat = cat.replace("Clauserel","Clause_rel").replace("Npro","N_pro").replace("Vaux","V_aux")
            if cat.startswith('GAP'):
                assert w=='_.'
                w = None
            if '.' in cat:
                cat, label = cat.split('.')
                cat = label + ' / ' + cat
            func = func.replace("DetHead","Det-Head").replace("ModHead","Mod-Head").replace("MarkerHead","Marker-Head").replace("HeadPrenucleus","Head-Prenucleus").replace("PCComp","PredComp/Comp")
            head = int(head)
            if head==root: head = 0
            nodes[i] = (w, func, cat, i, head)
            sent.append(w if w is not None else '--')
            children[head].append(i)

        def descendants(y):
            result = {y}
            for c in children[y]:
                result |= descendants(c)
            return result

        # Tree nodes need to be added top-down. So construct a topological sort of
        # nodes such that parents are always before their children
        queue = [0]
        for x in queue: # BFS
            queue.extend(sorted(children[x], key=lambda y: min(descendants(y))))

        for i in queue:
            w,func,cat,i,head = nodes[i]
            #Tree.add_token(self, token: str, deprel: str, constituent: str, i: int, head: int)
            # Called separately for terminal strings vs. non/preterminals
            tree.add_token(None, func, cat, i, head)    # proper nodes
            if w is not None:
                tree.add_token(w, None, None, None, i)  # terminal strings

        assert " ".join(sent)==tree.sentence(gaps=True)

        yield tree

def convert(inF, outF):
    """Given export data in `inF`, write CGEL trees to `outF`.
    To store in a string, consider passing an `io.StringIO` instance as `outF`."""

    for iSent,tree in enumerate(load(inF=inF), start=1):
        print(f'# sent_id = ???{iSent}', file=outF)
        print(f'# sent_num = {iSent}', file=outF)
        print(f'# text = ???', file=outF)
        print(f'# sent = {tree.sentence(gaps=True)}', file=outF)
        print(str(tree), file=outF)
        print(file=outF)

if __name__=='__main__':
    convert(inF=fileinput.input(), outF=sys.stdout)
