rules = [
    ['Clause', ('Subj', 'NP'), ('Head', 'VP')],
    ['NP', ('Det', 'DP'), ('Head', 'Nom')],
    ['Nom', ('Head', 'N')],
    ['Nom', ('Head', 'N'), ('Mod', 'Clause_rel')],
    ['Clause_rel', ('Marker', 'Subdr'), ('Head', 'Clause')],
    ['VP', ('Head', 'V')],
    ['VP', ('Head', 'V'), ('PredComp', 'NP')],
    ['VP', ('Head', 'V'), ('PredComp', 'AdjP')]
]

def cky(sentence):
    pass