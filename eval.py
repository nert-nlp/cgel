from cgel import Tree, trees
from collections import defaultdict
import Levenshtein
import glob

def edit_distance(tree1: Tree, tree2: Tree) -> int:
    # get the spans from both trees
    span1, span2 = tree1.get_spans(), tree2.get_spans()
    span_by_bounds = [defaultdict(list), defaultdict(list)]

    # group spans by bounds (left, right)
    # this maintains order by depth, e.g. NP -> Nom -> N
    for i, spans in enumerate([span1, span2]):
        for span in spans:
            span_by_bounds[i][(span.left, span.right)].append((span.node.deprel, span.node.constituent))
    
    # levenshtein distance operations
    ins, delt = 0, 0
    for bound in set(span_by_bounds[0].keys()) | set(span_by_bounds[1].keys()):
        seq1, seq2 = span_by_bounds[0][bound], span_by_bounds[1][bound]
        edit_ops = Levenshtein.editops(seq1, seq2)

        # each substitution op is counted as 1 delt + 1 ins
        for op in edit_ops:
            if op[0] != 'delete': ins += 1
            if op[0] != 'insert': delt += 1

    # precision: how much of tree2 is present in tree1? (n2 - ins) / n1
    # recall: how much of tree1 is present in tree2? (n1 - del) / n2
    dist = ins + delt
    prec = (len(span2) - ins) / len(span1)
    rec = (len(span1) - delt) / len(span2)
    
    # return scores
    # normalised: the max distance is if the sets of spans are disjoint, so divide by that
    return {
        'raw_dist': dist,
        'normalised_dist': dist / (len(span1) + len(span2)),
        'precision': prec,
        'recall': rec
    }

def test():
    for file in glob.glob("datasets/*.cgel"):
        with open(file) as f:
            for tree in trees(f, check_format=True):
                print(edit_distance(tree, tree))
                input()