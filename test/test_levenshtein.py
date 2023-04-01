from eval import levenshtein

def test_levenshtein():
    assert levenshtein([('a','a'), ('b','b')], [('a','a'), ('b','b')]) == (0.0, [])
    assert levenshtein([('a','a'), ('b','b')], [('a','a'), ('b','b')], matches=True) == (0.0, [('match', 0, 0), ('match', 1, 1)])
    assert levenshtein([('a','a'), ('b','b')], [('A','A'), ('b','b')]) == (1.0, [('substitute', 0, 0)])
    assert levenshtein([('a','a'), ('b','b'), ('ccc','ccc')], [('a','a'), ('B','b'), ('ccc','ccc')]) == (1.0, [('substitute', 1, 1)])
    assert levenshtein([], [('a','a'), ('B','b'), ('ccc','ccc')]) == (3.0, [('insert', 0, 0), ('insert', 0, 1), ('insert', 0, 2)])
    assert levenshtein([('a','a'), ('b','b'), ('c','c')], [('b','b'), ('c','c'), ('d','d')], matches=True) == (2.0, [('delete', 0, 0), ('match', 1, 0), ('match', 2, 1), ('insert', 3, 2)])
    assert levenshtein([('a','a'), ('b','b')], [('c','c'), ('b','b'), ('e','e'), ('f','f')]) == (3.0, [('substitute', 0, 0), ('insert', 2, 2), ('insert', 2, 3)])
    assert levenshtein(['a', 'a'], ['a', 'a', 'a'], matches=True) == (1.0, [('match', 0, 0), ('match', 1, 1), ('insert', 2, 2)])
