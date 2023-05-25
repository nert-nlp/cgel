from cgel import Tree, trees, Span
from edit_distance import levenshtein, TED

from collections import defaultdict, Counter
from typing import List, Tuple, Mapping
import glob
import sys
from tqdm import tqdm

def score_tree(tree1: Tree, tree2: Tree, includeCat=True, includeFxn=True, strict=False, extra_counts=Counter()) -> dict:
    """tree1: treated as gold
    tree2: treated as prediction"""

    # Store antecedent nodes by label
    antecedents = [{}, {}]
    for i, tree in enumerate([tree1, tree2]):
        for n, node in tree.tokens.items():
            extra_counts[('CAT',node.constituent,'gold' if i==0 else 'pred')] += 1
            if node.label and node.constituent!="GAP":
                assert node.label not in antecedents[i]
                antecedents[i][node.label] = n

    labeler = lambda node: (node.constituent if includeCat else None, 
                            node.deprel if includeFxn else None, 
                            node.lexeme, 
                            None)

    cost, editcosts, alignment = TED(tree1, tree2, labeler=labeler, SUB=1 if strict else float('-inf'))

    for n1,n2 in alignment.items():
        node1 = tree1.tokens[n1]
        node2 = tree2.tokens[n2]

        if node1.constituent==node2.constituent:
            extra_counts[('CAT',node2.constituent,'match')] += 1

        if node1.constituent=="GAP" and node2.constituent=="GAP":
            assert node1.label is not None
            assert node2.label is not None

            # Are gaps' antecedents aligned to each other?
            a1 = antecedents[0][node1.label]
            a2 = antecedents[1][node2.label]
            if alignment.get(a1) != a2:
                # No! Pay a penalty
                cost += 0.25
                editcosts['SUB'] += 0.25
                extra_counts[('CAT',node2.constituent,'match')] -= 1    # undo the addition from above

    precCost = editcosts['INS']  # present only in tree2 (treated as system output)
    recCost = editcosts['DEL']   # only in tree1
    precCost += editcosts['SUB']/2
    recCost += editcosts['SUB']/2

    # return scores
    # normalised: the max distance is if the sets of spans are disjoint, so divide by that
    return {
        'recall_cost': precCost,
        'precision_cost': recCost,
        #'gold_lexemes': gold_lexemes,
        'gold_size': len(tree1.tokens),
        'pred_size': len(tree2.tokens),
        'raw_dist': cost,
        'normalised_dist': cost / max(len(tree1.tokens), len(tree2.tokens)),
        'precision': precCost / len(tree2.tokens),
        'recall': recCost / len(tree1.tokens),
        'tree_acc': int(cost==0)
    }

def compute_summary_stats(avg, count):
    microP = (avg['pred_size'] - avg['precision_cost']) / avg['pred_size']
    microR = (avg['gold_size'] - avg['recall_cost']) / avg['gold_size']

    # compute macroaverages
    for metric in avg:
        if metric not in ['count']:
            avg[metric] /= count

    avg['count'] = count
    avg['μprecision'] = microP
    avg['μrecall'] = microR
    avg['f1'] = (2 * avg['precision'] * avg['recall']) / (avg['precision'] + avg['recall']) if \
        (avg['precision'] + avg['recall']) != 0.0 else 0.0
    avg['μf1'] = (2 * avg['μprecision'] * avg['μrecall']) / (avg['μprecision'] + avg['μrecall']) if \
        (avg['μprecision'] + avg['μrecall']) != 0.0 else 0.0

def test(gold, pred):
    avg = defaultdict(lambda: {
        'recall_cost': 0.0,
        'precision_cost': 0.0,
        #'gold_lexemes': 0,
        'gold_size': 0,
        'pred_size': 0,
        'raw_dist': 0.0,
        'normalised_dist': 0.0,
        'precision': 0.0,
        'recall': 0.0,
        'f1': 0.0,
        'gaps_gold': 0,
        'gaps_pred': 0,
        'gaps_correct': 0,
        'tree_acc': 0.0,  # exact match of the full tree
        'ted': 0
    })

    counts = Counter()
    count = 0
    with open(gold) as f, open(pred) as p:
        gold = [tree for tree in trees(f, check_format=True)]
        pred = [tree for tree in trees(p, check_format=True)]
        assert len(gold) == len(pred), "Both files should have the same number of trees."

        count = len(gold)
        for i in tqdm(range(len(gold))):
            # normal edit distances
            res = score_tree(gold[i], pred[i], includeCat=True, includeFxn=True, extra_counts=counts)

            # subcategorise tree types
            # gold_lexemes = res['gold_lexemes']
            # if gold_lexemes <= 40:
            #     confs['<=40'] += 1
            #     if gold_lexemes <= 10:
            #         confs['<=10'] += 1
            #     elif gold_lexemes <= 20:
            #         confs['(10,20]'] += 1
            #     elif gold_lexemes <= 30:
            #         confs['(20,30]'] += 1
            #     else:
            #         confs['(30,40]'] += 1   # Note: may not make top 100 results in printout of `confs`
            # else:
            #     confs['>40'] += 1

            resUnlab = score_tree(gold[i], pred[i], includeCat=False, includeFxn=False, strict=False)
            resNoCat = score_tree(gold[i], pred[i], includeCat=False, includeFxn=True, strict=False)
            resNoFxn = score_tree(gold[i], pred[i], includeCat=True, includeFxn=False, strict=False)
            resStrict = score_tree(gold[i], pred[i], includeCat=True, includeFxn=True, strict=True)
            for metric in res:
                avg['flex'][metric] += res[metric]
                avg['unlab'][metric] += resUnlab[metric]
                avg['nocat'][metric] += resNoCat[metric]
                avg['nofxn'][metric] += resNoFxn[metric]
                avg['strict'][metric] += resStrict[metric]

            # tree edit distance
            # ted = TED(gold[i], pred[i])[0]
            # avg['strict']['ted'] += ted


    #print(confs.most_common(100))

    # print stats
    gaps_gold = counts[('CAT','GAP','gold')]
    gaps_pred = counts[('CAT','GAP','pred')]
    gaps_correct = counts[('CAT','GAP','match')]
    gaps_prec = 0 if gaps_pred==0 else gaps_correct/gaps_pred
    gaps_rec = 0 if gaps_gold==0 else gaps_correct/gaps_gold
    gaps_f1 = 2*gaps_prec*gaps_rec
    if gaps_f1>0.0:
        gaps_f1 /= gaps_prec + gaps_rec
    report = (f"count={count}, gold_constits={avg['flex']['gold_size']} ({gaps_gold} gaps), "
            f"pred_constits={avg['flex']['pred_size']} ({gaps_pred} gaps)\n         ")
    rows = ['microF   ', 'microP   ', 'microR   ', 'avgcost  ', 'avgPcost ', 'avgRcost ']
    for condition in ('unlab', 'flex', 'nocat', 'nofxn', 'strict'):
        compute_summary_stats(avg[condition], count)
        report += f'{condition:8}'
        rows[0] += f"{avg[condition]['μf1']:.1%}   "
        rows[1] += f"{avg[condition]['μprecision']:.1%}   "
        rows[2] += f"{avg[condition]['μrecall']:.1%}   "
        rows[3] += f"{avg[condition]['precision_cost']+avg[condition]['recall_cost']:>5.2f}   "
        rows[4] += f"{avg[condition]['precision_cost']:>5.2f}   "
        rows[5] += f"{avg[condition]['recall_cost']:>5.2f}   "
    report += 'TreeAcc Gaps'
    rows[0] += f"{avg['flex']['tree_acc']:.1%}   {gaps_f1:.1%}"
    print("", report, *rows, sep="\n")
    #print(f"\nTree edit distance: {avg['strict']['ted']:.2f} (avg)")

def main():
    assert len(sys.argv) == 3, "Need 2 arguments (filenames)"
    test(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
