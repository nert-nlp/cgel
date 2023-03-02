from cgel import Tree, trees
from collections import defaultdict
import Levenshtein

def edit_distance(tree1: Tree, tree2: Tree) -> int:
    # get the spans from both trees
    span1, span2 = tree1.get_spans(), tree2.get_spans()
    span_by_bounds = [defaultdict(list), defaultdict(list)]

    # group spans by bounds (left, right)
    # this maintains order by depth, e.g. NP -> Nom -> N
    for i, spans in enumerate([span1, span2]):
        for span in spans:
            span_by_bounds[i][(span.left, span.right)].append((span.node.deprel, span.node.constituent))
    
    # calculate sum of levenshtein distances
    dist: int = 0
    for bound in set(span_by_bounds[0].keys()) | set(span_by_bounds[1].keys()):
        dist += Levenshtein.distance(span_by_bounds[0][bound], span_by_bounds[1][bound])
    
    # return scores
    # normalised: the max distance is if the sets of spans are disjoint, so divide by that
    return {
        'raw_dist': dist,
        'normalised_dist': dist / (len(span1) + len(span2))
    }