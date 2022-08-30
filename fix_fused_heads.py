import cgel

class Tree(cgel.Tree):

    def fix_fused_heads(self):
        return self._fix_fused_heads_rec(self.get_root())
    
    def _fix_fused_heads_rec(self, cur):
        children = self.children[cur]
        head_fxns = [self.tokens[x].deprel for x in children if 'Head' in self.tokens[x].deprel]
        change = False

        # check if fused head
        if len(head_fxns) != 1 and not all(self.tokens[x].deprel in {'Flat','Compounding'} for x in children):
            true_heads = [x for x in children if self.tokens[x].deprel == 'Head']
            
            # if fused-head and head are siblings, and only one head
            # then the fused-head is moved to be a child of the actual head
            # other dependents are not moved
            if len(true_heads) == 1:
                change = True
                true_head = true_heads[0]
                if self.tokens[true_head].constituent == 'GAP':
                    print(self.sentence())
                    input()
                else:
                    for child in children:
                        if child != true_head and 'Head' in self.tokens[child].deprel:
                            # prepend to preserve order (actual head follows fused-head)
                            self.children[true_head].insert(0, child)
                            self.children[cur].remove(child)
        
        for i in self.children[cur]:
            change = change or self._fix_fused_heads_rec(i)
        
        return change
                


cgel.Tree = Tree

for file in ['datasets/twitter.cgel', 'datasets/ewt.cgel']:
    with open(file) as f:

        with open(f'{file}2', 'w') as fout:
            for tree in cgel.trees(f, check_format=True):
                if tree.fix_fused_heads():
                    pass
                fout.write(tree.draw(include_metadata=True))
                fout.write('\n\n')