import cgel
"""
CGELBank 1.0 conventions put :p punctuations before the next lexical token.
Move to the previous lexical token, with exceptions for "(" and "[".

Run in root directory as python -m scripts.move_punct
"""
for file in ['datasets/twitter.cgel', 'datasets/ewt.cgel',
             'datasets/ewt-test_iaa50.cgel', 'datasets/ewt-test_pilot5.cgel',
             'datasets/trial/ewt-trial.cgel', 'datasets/trial/twitter-etc-trial.cgel']:
    with open(file) as f:

        with open(f'{file}2', 'w') as fout:
            for tree in cgel.trees(f, check_format=True):
                terminals = tree.terminals(gaps=False)
                for i,t in enumerate(terminals):
                    if i==0: continue
                    while t.prepunct and not (set(t.prepunct[0]) & {"(", "["}):
                        p = t.prepunct.pop(0)
                        terminals[i-1].postpunct.append(p)

                fout.write(tree.draw(include_metadata=True))
                fout.write('\n\n')
