from eval import levenshtein, tree_edit_distance, TED
from cgel import trees

from collections import Counter

def test_levenshtein_seqs():
    assert levenshtein([('a','a'), ('b','b')], [('a','a'), ('b','b')]) == (0.0, [])
    assert levenshtein([('a','a'), ('b','b')], [('a','a'), ('b','b')], matches=True) == (0.0, [('match', 0, 0), ('match', 1, 1)])
    assert levenshtein([('a','a'), ('b','b')], [('A','A'), ('b','b')]) == (1.0, [('substitute', 0, 0)])
    assert levenshtein([('a','a'), ('b','b'), ('ccc','ccc')], [('a','a'), ('B','b'), ('ccc','ccc')]) == (1.0, [('substitute', 1, 1)])
    assert levenshtein([], [('a','a'), ('B','b'), ('ccc','ccc')]) == (3.0, [('insert', 0, 0), ('insert', 0, 1), ('insert', 0, 2)])
    assert levenshtein([('a','a'), ('b','b'), ('c','c')], [('b','b'), ('c','c'), ('d','d')], matches=True) == (2.0, [('delete', 0, 0), ('match', 1, 0), ('match', 2, 1), ('insert', 3, 2)])
    assert levenshtein([('a','a'), ('b','b')], [('c','c'), ('b','b'), ('e','e'), ('f','f')]) == (3.0, [('substitute', 0, 0), ('insert', 2, 2), ('insert', 2, 3)])
    assert levenshtein(['a', 'a'], ['a', 'a', 'a'], matches=True) == (1.0, [('match', 0, 0), ('match', 1, 1), ('insert', 2, 2)])

def test_ted_trees():
    with open('test/test1.cgel') as f, open('test/test2.cgel') as g:
        F = [tree for tree in trees(f, check_format=True)]
        G = [tree for tree in trees(g, check_format=True)]

        for i in range(len(F)):
            assert tree_edit_distance(F[i], G[i]) == int(G[i].metadata['expected_ted'])

def test_TED():
    with open('test/test1.cgel') as f, open('test/test2.cgel') as g:
        F = [tree for tree in trees(f, check_format=True)]
        G = [tree for tree in trees(g, check_format=True)]

        totEditcosts = Counter()
        nFnodes = nGnodes = 0
        for i in range(len(F)):
            nFnodes += len(F[i].tokens)
            nGnodes += len(G[i].tokens)
            cost, editcosts, alignment = TED(F[i], G[i])
            assert sum(editcosts.values())==cost
            assert cost == int(G[i].metadata['expected_ted']),(i,cost,G[i].metadata['expected_ted'],editcosts,alignment)
            if (cwted := G[i].metadata.get('expected_componentwise_ted')) is not None:
                cost, editcosts, alignment = TED(F[i], G[i], SUB=float('-inf'))
                assert sum(editcosts.values())==cost
                assert cost == float(cwted),(i,cost,editcosts,cwted,alignment)
                totEditcosts += editcosts

        precCost = totEditcosts['DEL']  # present only in T1 (treated as system output)
        recCost = totEditcosts['INS']   # only in T2
        precCost += totEditcosts['SUB']/2
        recCost += totEditcosts['SUB']/2
        print(f'''
    Cost: total={sum(totEditcosts.values())} breakdown={totEditcosts}
    Precision: cost={precCost} T1 nodes={nFnodes} ratio={1 - precCost/nFnodes:.2}
       Recall: cost={recCost} T2 nodes={nGnodes} ratio={1 - recCost/nGnodes:.2}
''')
