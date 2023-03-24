level = {
    ('Subj', 'V'): 'Clause',
    ('Subj', 'V_aux'): 'Clause',
    ('Obj', 'V'): 'VP',
    ('Obj', 'V_aux'): 'VP',
    ('PredComp', 'V'): 'VP',
    ('PredComp', 'V_aux'): 'VP',
    ('Comp', 'V'): 'VP',
    ('Comp', 'V_aux'): 'VP',
    ('Mod', 'V'): 'Clause',
    ('Mod', 'V_aux'): 'Clause',
    ('Obj_ind', 'V'): 'VP',
    ('Obj_ind', 'V_aux'): 'VP',
    ('Det', 'N'): 'NP',
    ('Mod', 'N'): 'Nom',
    ('Flat', 'N'): 'N'
}

projections = {
    'V': ['VP', 'Clause'],
    'V_aux': ['VP', 'Clause'],
    'N': ['Nom', 'NP', 'Clause'],
    'N_pro': ['Nom', 'NP', 'Clause'],
    'D': ['DP', 'Clause'],
    'Adj': ['AdjP', 'Clause'],
    'Adv': ['AdvP', 'Clause'],
    'P': ['PP', 'Clause']
}