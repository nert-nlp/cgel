import cgel
import sys

def test_validate():
    for file in ['datasets/ewt.cgel', 'datasets/twitter.cgel']:
        with open(file) as f:
            for tree in cgel.trees(f, check_format=True):
                # check_format=True ensures that the generated tree structure matches the input

                # also check that the sentence line matches
                s = tree.sentence(gaps=True)
                assert tree.sent==s,(tree.sent,s)

                warnings = tree.validate() # warning count is cumulative

    print(f'{warnings} warnings/notices', file=sys.stderr)
    assert warnings == 0