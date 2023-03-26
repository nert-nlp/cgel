from cgel import Tree, trees
from collections import defaultdict
from typing import List, Tuple
import glob
import sys

def levenshtein(
    s1: List[Tuple[str, str]],
    s2: List[Tuple[str, str]],
    ins: float = 1.0,
    dlt: float = 1.0,
    sub: float = 1.0
) -> Tuple[float, List[Tuple[str, int, int]]]:
    """Calculate weighted Levenshtein distance and associated optimal edit
    operations to go from s1 to s2.

    >>> levenshtein([('a','a'), ('b','b')], [('a','a'), ('b','b')])
    (0.0, [])
    >>> levenshtein([('a','a'), ('b','b')], [('A','A'), ('b','b')])
    (1.0, [('substitute', 0, 0)])
    >>> levenshtein([('a','a'), ('b','b'), ('ccc','ccc')], [('a','a'), ('B','b'), ('ccc','ccc')])
    (1.0, [('substitute', 1, 1)])
    >>> levenshtein([], [('a','a'), ('B','b'), ('ccc','ccc')])
    (3.0, [('insert', 0, 0), ('insert', 0, 1), ('insert', 0, 2)])
    >>> levenshtein([('a','a'), ('b','b')], [('b','b'), ('ccc','ccc')])
    (2.0, [('delete', 0, 0), ('insert', 2, 1)])
    >>> levenshtein([('a','a'), ('b','b')], [('c','c'), ('b','b'), ('e','e'), ('f','f')])
    (3.0, [('substitute', 0, 0), ('insert', 2, 2), ('insert', 2, 3)])
    """

    # fill out matrix of size (len(s1) + 1) x (len(s2) + 1)
    matrix: List[List[Tuple]] = [[() for _ in range(len(s2) + 1)] for _ in range(len(s1) + 1)]
    for j in range(len(s2) + 1): matrix[0][j] = (j, 'insert')
    for i in range(len(s1) + 1): matrix[i][0] = (i, 'delete')
    for i in range(1, len(s1) + 1):
        for j in range(1, len(s2) + 1):
            if s1[i - 1] == s2[j - 1]: matrix[i][j] = (matrix[i - 1][j - 1][0], 'N')
            else:
                matrix[i][j] = min(
                    (matrix[i - 1][j][0] + dlt, 'delete'),
                    (matrix[i][j - 1][0] + ins, 'insert'),
                    (matrix[i - 1][j - 1][0] + sub, 'substitute')
                )

    # extract edit operations + calculate cost
    edits = []
    i, j = len(s1), len(s2)
    cost = 0.0
    while (i != 0 or j != 0):
        editOp = matrix[i][j][1]

        if editOp == 'delete':
            cost += dlt
            i -= 1
        elif editOp == 'insert':
            cost += ins
            j -= 1
        else:
            if editOp == 'substitute': cost += sub
            i -= 1
            j -= 1

        if editOp != 'N':   # 'N' = no more edits
            edits.append((editOp, i, j))

    return cost, edits[::-1]

def edit_distance(tree1: Tree, tree2: Tree, includeCat=True, includeFxn=True) -> dict:
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
        levcost, edits = levenshtein(seq1, seq2, 1.0, 1.0, 1.0)

        # each substitution op is counted as 0.5 delt + 0.5 ins
        for (op,i,j) in edits:
            if op == 'delete': delt += 1
            if op == 'insert': ins += 1
            else:
                delt += 0.5
                ins += 0.5

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
        'valid': (string1 == string2, string1, string2),
    }

def test(gold, pred):
    avg = {
        'ins': 0.0,
        'del': 0.0,
        'gold_size': 0,
        'pred_size': 0,
        'raw_dist': 0.0,
        'normalised_dist': 0.0,
        'precision': 0.0,
        'recall': 0.0,
        'f1': 0.0,
        'tree_acc': 0.0,  # exact match of the full tree
        'valid': 0,
    }

    count = 0
    with open(gold) as f, open(pred) as p:
        gold = [tree for tree in trees(f, check_format=True)]
        pred = [tree for tree in trees(p, check_format=True)]
        assert len(gold) == len(pred), "Both files should have the same number of trees."

        count = len(gold)
        for i in range(len(gold)):
            res = edit_distance(gold[i], pred[i], includeCat=True, includeFxn=True)
            res['valid'], string1, string2 = res['valid']
            if res['valid']:
                for metric in res:
                    avg[metric] += res[metric]
            else:
                print(f"Tree #{i} not aligned.")
                print("    ", string1)
                print("    ", string2)

    microP = (avg['pred_size'] - avg['ins']) / avg['pred_size']
    microR = (avg['gold_size'] - avg['del']) / avg['gold_size']

    # compute macroaverages of valid (string-matched) pairs only
    for metric in avg:
        if metric not in ['valid', 'count']:
            avg[metric] /= avg['valid']

    avg['count'] = count
    avg['μprecision'] = microP
    avg['μrecall'] = microR
    avg['f1'] = (2 * avg['precision'] * avg['recall']) / (avg['precision'] + avg['recall']) if \
        (avg['precision'] + avg['recall']) != 0.0 else 0.0
    avg['μf1'] = (2 * avg['μprecision'] * avg['μrecall']) / (avg['μprecision'] + avg['μrecall']) if \
        (avg['μprecision'] + avg['μrecall']) != 0.0 else 0.0

    print(avg)

def main():
    assert len(sys.argv) == 3, "Need 2 arguments (filenames)"
    test(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
