level = {
    ('Subj', 'V'): 'Clause',
    ('Subj', 'Vaux'): 'Clause',
    ('Obj', 'V'): 'VP',
    ('Obj', 'Vaux'): 'VP',
    ('PredComp', 'V'): 'VP',
    ('PredComp', 'Vaux'): 'VP',
    ('Comp', 'V'): 'VP',
    ('Comp', 'Vaux'): 'VP',
    ('Obj_ind', 'V'): 'VP',
    ('Obj_ind', 'Vaux'): 'VP',
    ('Det', 'N'): 'NP',
    ('Mod', 'N'): 'Nom',
    ('Flat', 'N'): 'N'
}

projections = {
    'V': ['VP', 'Clause'],
    'V_aux': ['VP', 'Clause'],
    'N': ['Nom', 'NP', 'Clause'],
    'D': ['DP', 'Clause'],
    'Adj': ['AdjP', 'Clause'],
    'Adv': ['AdvP', 'Clause'],
    'P': ['PP', 'Clause']
}