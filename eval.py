from cgel import Tree, trees
from collections import defaultdict
import Levenshtein
import glob
import sys

def edit_distance(tree1: Tree, tree2: Tree, includeCat=True, includeFxn=True) -> int:
    # get the spans from both trees
    (span1, string1), (span2, string2) = tree1.get_spans(), tree2.get_spans()
    span_by_bounds = [defaultdict(list), defaultdict(list)]
    string1 = string1.lower()
    string2 = string2.lower()

    # group spans by bounds (left, right)
    # this maintains order by depth, e.g. NP -> Nom -> N
    for i, spans in enumerate([span1, span2]):
        for span in spans:
            cat = span.node.constituent if includeCat else None
            fxn = span.node.deprel if includeFxn else None
            span_by_bounds[i][(span.left, span.right)].append((fxn, cat))

    # levenshtein distance operations to edit the 1st tree to match the 2nd tree
    ins, delt = 0, 0
    for bound in set(span_by_bounds[0].keys()) | set(span_by_bounds[1].keys()):
        seq1, seq2 = span_by_bounds[0][bound], span_by_bounds[1][bound]
        edit_ops = Levenshtein.editops(seq1, seq2)

        # each substitution op is counted as 1 delt + 1 ins
        for op in edit_ops:
            if op[0] != 'delete': ins += 1
            if op[0] != 'insert': delt += 1

    # precision: how much of tree2 is present in tree1? (n2 - ins) / n2
    # recall: how much of tree1 is present in tree2? (n1 - del) / n1
    dist = ins + delt
    prec = (len(span2) - ins) / len(span2)
    rec = (len(span1) - delt) / len(span1)

    # return scores
    # normalised: the max distance is if the sets of spans are disjoint, so divide by that
    return {
        'ins': ins,
        'del': delt,
        'gold_size': len(span1),
        'pred_size': len(span2),
        'raw_dist': dist,
        'normalised_dist': dist / (len(span1) + len(span2)),
        'precision': prec,
        'recall': rec,
        'tree_acc': int(dist==0),
        'valid': string1 == string2
    }

def test(gold, pred):
    avg = {
        'ins': 0,
        'del': 0,
        'gold_size': 0,
        'pred_size': 0,
        'raw_dist': 0,
        'normalised_dist': 0,
        'precision': 0,
        'recall': 0,
        'tree_acc': 0,  # exact match of the full tree
        'valid': 0,
    }

    count = 0
    with open(gold) as f, open(pred) as p:
        gold = [tree for tree in trees(f, check_format=True)]
        pred = [tree for tree in trees(p, check_format=True)]
        count = len(gold)
        for i in range(len(gold)):
            res = edit_distance(gold[i], pred[i], includeCat=True, includeFxn=True)
            if res['valid']:
                for metric in res:
                    avg[metric] += res[metric]
    microP = (avg['pred_size'] - avg['ins']) / avg['pred_size']
    microR = (avg['gold_size'] - avg['del']) / avg['gold_size']
    # compute macroaverages of valid (string-matched) pairs only
    for metric in avg:
        if metric not in ['valid', 'count']:
            avg[metric] /= avg['valid']
    avg['count'] = count
    avg['μprecision'] = microP
    avg['μrecall'] = microR

    print(avg)

def main():
    assert len(sys.argv) == 3, "Need 2 arguments (filenames)"
    test(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
