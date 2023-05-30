import cgel
from cgel import eprint

class Tree(cgel.Tree):

    def remove_lexical_unary(self):
        return self._remove_lexical_unary_rec(self.get_root())

    def _remove_lexical_unary_rec(self, c):
        LEX_projecting = {'N': 'Nom', 'N_pro': 'Nom', 'V': 'VP', 'V_aux': 'VP',
            'D': 'DP', 'P': 'PP', 'Adj': 'AdjP', 'Adv': 'AdvP', 'Int': 'IntP'}

        ch = self.tokens[c]
        p = ch.head
        par = self.tokens.get(p)

        children = self.children[c]
        head_fxns = [self.tokens[x].deprel for x in children if 'Head' in self.tokens[x].deprel]
        change = False

        for i in self.children[c]:
            change = self._remove_lexical_unary_rec(i) or change

        # Lexical Projection Principle
        if ch.constituent in LEX_projecting:
            if ch.deprel=='Flat':
                assert par.constituent==ch.constituent and ch.constituent in {'D','N'}
            else:
                # lexical item should project a phrasal category
                if not (ch.deprel=='Head' and par.constituent==LEX_projecting[ch.constituent]):
                    if ch.deprel=='Prenucleus' and ch.constituent=='V_aux':
                        # exception: Clause :Prenucleus V_aux
                        pass
                    else:
                        eprint("LEXICAL PROJECTION FAILURE\n"+self.draw_rec(p,0))
                # and that phrase MAY contain complements/modifiers (change from before)
                # i.e. if the parent node is unary, there should not be a grandparent node of the same type
                if len(self.children[p])==1:
                    gpar = self.tokens[par.head]
                    if par.constituent==gpar.constituent and ch.deprel==par.deprel=='Head' and gpar.deprel!='Coordinate':
                        #eprint('Lexical node is too deep:', self.draw_rec(c,0))
                        # Delete `par` node (intermediate layer)
                        self.children[p].remove(c)
                        i = self.children[par.head].index(p)
                        self.children[par.head][i] = c
                        if par.label:
                            assert gpar.label is None
                            gpar.label = par.label
                        assert not par.note
                        ch.head = par.head
                        change = True

        return change



cgel.Tree = Tree

for file in ['../datasets/twitter.cgel', '../datasets/ewt.cgel']:
    with open(file) as f:

        with open(f'{file}2', 'w') as fout:
            for tree in cgel.trees(f, check_format=True):
                if tree.remove_lexical_unary():
                    pass
                fout.write(tree.draw(include_metadata=True))
                fout.write('\n\n')
