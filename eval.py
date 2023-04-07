from cgel import Tree, trees, Span
from collections import defaultdict, Counter
from typing import List, Tuple, Mapping
import glob
import sys

def levenshtein(
    s1: List,
    s2: List,
    ins: float = 1.0,
    dlt: float = 1.0,
    sub: float = 1.0,
    matches = False # include matching elements in list of edits?
) -> Tuple[float, List[Tuple[str, int, int]]]:
    """Calculate weighted Levenshtein distance and associated optimal edit
    operations to go from s1 to s2."""

    # fill out matrix of size (len(s1) + 1) x (len(s2) + 1)
    matrix: List[List[Tuple]] = [[() for _ in range(len(s2) + 1)] for _ in range(len(s1) + 1)]
    for j in range(len(s2) + 1): matrix[0][j] = (j, 'insert')
    for i in range(len(s1) + 1): matrix[i][0] = (i, 'delete')
    for i in range(1, len(s1) + 1):
        for j in range(1, len(s2) + 1):
            matrix[i][j] = min(
                (matrix[i - 1][j][0] + dlt, 'delete'),
                (matrix[i][j - 1][0] + ins, 'insert'),
                (matrix[i - 1][j - 1][0] + sub, 'substitute')
            )
            if s1[i - 1] == s2[j - 1] and matrix[i - 1][j - 1][0] < matrix[i][j][0]:
                # Break ties between match and edit in favor of the edit.
                # This has the effect of preferring edits later in the sequence
                # (when following backtraces from the end, it frontloads them,
                # so that there will be more matches early in the sequence).
                matrix[i][j] = (matrix[i - 1][j - 1][0], 'match')

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

        if matches or editOp != 'match':
            edits.append((editOp, i, j))

    return cost, edits[::-1]

def edit_distance(tree1: Tree, tree2: Tree, includeCat=True, includeFxn=True, strict=False, confusions=Counter()) -> dict:
    # get the spans from both trees
    (span1, string1), (span2, string2) = tree1.get_spans(), tree2.get_spans()
    span_by_bounds: List[Mapping[Tuple[int,int], List[Span]]] = [defaultdict(list), defaultdict(list)]
    string1 = string1.lower()
    string2 = string2.lower()

    # group spans by bounds (left, right)
    # this maintains order by depth, e.g. NP -> Nom -> N
    antecedents = [{}, {}]
    gaps_gold = gaps_pred = gaps_correct = 0
    gold_lexemes = 0
    for i, spans in enumerate([span1, span2]):
        for span in spans:
            span_by_bounds[i][(span.left, span.right)].append(span)
            if span.node.constituent!='GAP':
                if i==0 and span.node.lexeme is not None:
                    gold_lexemes += 1
                if span.node.label:
                    assert span.node.label not in antecedents[i]
                    antecedents[i][span.node.label] = span

    gaps = []
    aligned = {}    # pred tree span -> gold tree span for SUBSTITUTE and MATCH edits

    # levenshtein distance operations to edit the 1st tree to match the 2nd tree
    ins, delt = 0, 0
    for bound in set(span_by_bounds[0].keys()) | set(span_by_bounds[1].keys()):
        seq1, seq2 = span_by_bounds[0][bound][::-1], span_by_bounds[1][bound][::-1]
        # sequences are in bottom-up order so that terminals will usually be aligned
        seq1CatFxn = [(span.node.constituent if includeCat else None, 
                       span.node.deprel if includeFxn else None) for span in seq1]
        seq2CatFxn = [(span.node.constituent if includeCat else None, 
                       span.node.deprel if includeFxn else None) for span in seq2]
        levcost, edits = levenshtein(seq1CatFxn, seq2CatFxn, 1.0, 1.0, 1.0, matches=True)
        # TODO: ensure gaps are only aligned to gaps

        for (op,i,j) in edits:
            confusions[op] += 1
            if op == 'delete':
                delt += 1
                node1 = seq1[i].node
                confusions[node1.constituent,''] += 1
                confusions[':'+node1.deprel,''] += 1
                if seq1[i].node.constituent=='GAP':
                    gaps_gold += 1
            elif op == 'insert':
                ins += 1
                node2 = seq2[j].node
                confusions['',node2.constituent] += 1
                confusions['',':'+node2.deprel] += 1
                if seq2[j].node.constituent=='GAP':
                    gaps_pred += 1
            else:   # pair of aligned nodes (whether cat and fxn match or not)
                assert op in ('substitute','match'),op
                aligned[seq2[j]] = seq1[i]
                node1 = seq1[i].node
                node2 = seq2[j].node
                confusions[node1.constituent,node2.constituent] += 1
                confusions[':'+node1.deprel,':'+node2.deprel] += 1

                """
                Compute partial-credit substitution cost:
                - Nonterminals: 0.25 for wrong function, 0.25 for wrong category (leave 0.5 credit for span)
                - Lexical terminals: 0.25 for wrong function, 0.25 for wrong category, 0.25 for wrong normalized string (leave 0.25 credit for token span)
                - Gap terminals: 0.25 for wrong function, 0.25 for wrong antecedent span (leave 0.5 credit for gap)
                """
                catPenalty = 0.25 if includeCat and node1.constituent!=node2.constituent else 0.0
                fxnPenalty = 0.25 if includeFxn and node1.deprel!=node2.deprel else 0.0
                confusions['catPenalty'] += int(catPenalty*4)
                confusions['fxnPenalty'] += int(fxnPenalty*4)
                if node1.constituent=='GAP':
                    assert node2.constituent=='GAP'
                    gaps.append((node1,node2,catPenalty,fxnPenalty)) # store for later
                    # we can't score them until the all nodes including antecendents have been aligned
                    continue
                elif node1.lexeme is not None:   # Lexical node
                    s1 = node1.lexeme
                    s2 = node2.lexeme
                    assert s2 is not None,(edits,op,str(node1),[span.node.constituent for span in seq1],str(node2),[span.node.constituent for span in seq2])
                    strPenalty = 0.25 if s1!=s2 else 0.0
                    subcost = catPenalty + fxnPenalty + strPenalty
                    confusions['strPenalty'] += int(strPenalty*4)
                else:   # Nonterminal
                    assert node2.constituent!='GAP'
                    assert node2.lexeme is None
                    subcost = catPenalty + fxnPenalty

                """
                In strict mode, don't give partial credit.
                """
                if strict and subcost>0:    # a substitution, or a match where the gap antecedent or token string is wrong
                    subcost = 1.0

                """
                For computing precision/recall, substitution cost is counted half toward deletion 
                and half toward insertion.
                """
                delt += subcost/2
                ins += subcost/2

    # score gaps
    for node1,node2,catPenalty,fxnPenalty in gaps:
        # check if antecedents are aligned
        ant1 = antecedents[0][node1.label]
        ant2 = antecedents[1][node2.label]
        aligned_to_ant2 = aligned.get(ant2)
        #if aligned_to_ant2 is None:
        #    assert False,(ant2,aligned.keys())
        antPenalty = 0.0 if aligned_to_ant2 is ant1 else 0.25
        gaps_gold += 1
        gaps_pred += 1
        if antPenalty==0.0:
            gaps_correct += 1
        subcost = catPenalty + fxnPenalty + antPenalty
        confusions['antPenalty'] += int(antPenalty*4)

        """
        In strict mode, don't give partial credit.
        """
        if strict and subcost>0:    # a substitution, or a match where the gap antecedent or token string is wrong
            subcost = 1.0

        """
        For computing precision/recall, substitution cost is counted half toward deletion 
        and half toward insertion.
        """
        delt += subcost/2
        ins += subcost/2

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
        'gold_lexemes': gold_lexemes,
        'gold_size': len(span1),
        'pred_size': len(span2),
        'raw_dist': dist,
        'normalised_dist': dist / max(len(span1), len(span2)),
        'precision': prec,
        'recall': rec,
        'gaps_gold': gaps_gold,
        'gaps_pred': gaps_pred,
        'gaps_correct': gaps_correct,
        'tree_acc': int(dist==0),
        'valid': (string1 == string2, string1, string2),
    }

def compute_summary_stats(avg, count, valid):
    microP = (avg['pred_size'] - avg['ins']) / avg['pred_size']
    microR = (avg['gold_size'] - avg['del']) / avg['gold_size']

    # compute macroaverages of valid (string-matched) pairs only
    avg['valid'] = valid
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

def test(gold, pred):
    avg = defaultdict(lambda: {
        'ins': 0.0,
        'del': 0.0,
        'gold_lexemes': 0,
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
        'valid': 0,
    })

    confs = Counter()
    count = 0
    with open(gold) as f, open(pred) as p:
        gold = [tree for tree in trees(f, check_format=True)]
        pred = [tree for tree in trees(p, check_format=True)]
        assert len(gold) == len(pred), "Both files should have the same number of trees."

        count = len(gold)
        for i in range(len(gold)):
            res = edit_distance(gold[i], pred[i], includeCat=True, includeFxn=True, confusions=confs)
            gold_lexemes = res['gold_lexemes']
            if gold_lexemes <= 40:
                confs['<=40'] += 1
                if gold_lexemes <= 10:
                    confs['<=10'] += 1
                elif gold_lexemes <= 20:
                    confs['(10,20]'] += 1
                elif gold_lexemes <= 30:
                    confs['(20,30]'] += 1
                else:
                    confs['(30,40]'] += 1   # Note: may not make top 100 results in printout of `confs`
            else:
                confs['>40'] += 1
            res['valid'], string1, string2 = res['valid']
            if res['valid']:
                resUnlab = edit_distance(gold[i], pred[i], includeCat=False, includeFxn=False, strict=False)
                resNoCat = edit_distance(gold[i], pred[i], includeCat=False, includeFxn=True, strict=False)
                resNoFxn = edit_distance(gold[i], pred[i], includeCat=True, includeFxn=False, strict=False)
                resStrict = edit_distance(gold[i], pred[i], includeCat=True, includeFxn=True, strict=True)
                for metric in res:
                    avg['flex'][metric] += res[metric]
                    if metric!='valid':
                        avg['unlab'][metric] += resUnlab[metric]
                        avg['nocat'][metric] += resNoCat[metric]
                        avg['nofxn'][metric] += resNoFxn[metric]
                        avg['strict'][metric] += resStrict[metric]
            else:
                print(f"Tree #{i} not aligned.")
                print("    ", string1)
                print("    ", string2)

    print(confs.most_common(100))

    gaps_gold = avg['flex']['gaps_gold']
    gaps_pred = avg['flex']['gaps_pred']
    gaps_correct = avg['flex']['gaps_correct']
    gaps_prec = 0 if gaps_pred==0 else gaps_correct/gaps_pred
    gaps_rec = 0 if gaps_gold==0 else gaps_correct/gaps_gold
    gaps_f1 = 2*gaps_prec*gaps_rec
    if gaps_f1>0.0:
        gaps_f1 /= gaps_prec + gaps_rec
    report = (f"count={count}, valid={avg['flex']['valid']}, gold_constits={avg['flex']['gold_size']} ({gaps_gold} gaps), "
            f"pred_constits={avg['flex']['pred_size']} ({gaps_pred} gaps)\n")
    rows = ['' for _ in range(3)]
    for condition in ('unlab', 'flex', 'nocat', 'nofxn', 'strict'):
        compute_summary_stats(avg[condition], count, avg['flex']['valid'])
        report += f'{condition:8}'
        rows[0] += f"{avg[condition]['μf1']:.1%}   "
        rows[1] += f"{avg[condition]['μprecision']:.1%}   "
        rows[2] += f"{avg[condition]['μrecall']:.1%}   "
    report += 'TreeAcc Gaps'
    rows[0] += f"{avg['flex']['tree_acc']:.1%}   {gaps_f1:.1%}"
    print("", report, *rows, sep="\n")

def main():
    assert len(sys.argv) == 3, "Need 2 arguments (filenames)"
    test(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
