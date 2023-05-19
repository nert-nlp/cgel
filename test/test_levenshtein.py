from eval import levenshtein, tree_edit_distance, TED
from cgel import trees

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

        for i in range(len(F)):
            cost, edits = TED(F[i], G[i])
            assert cost == int(G[i].metadata['expected_ted']),(i,cost,G[i].metadata['expected_ted'],edits)
            if (cwted := G[i].metadata.get('expected_componentwise_ted')) is not None:
                cost, edits = TED(F[i], G[i], SUB=float('-inf'))
                assert cost == float(cwted),(i,cost,cwted,edits)
