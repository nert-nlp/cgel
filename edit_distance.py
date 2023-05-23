from cgel import Tree, Node, trees, Span
from typing import List, Tuple, Mapping

from collections import Counter

DEBUG = False

def TED(T1: Tree, T2: Tree,
        INS: float = 1, DEL: float = 1, SUB: float = 1) -> Tuple[float,Counter,Mapping[int,int]]:
    """
    TREE EDIT DISTANCE
    Implementation of Milos Simic's pseudocode in <https://www.baeldung.com/cs/tree-edit-distance>,
    a memoized version of Zhang and Shasha's algorithm.

    Returns total cost, cost breakdown by edit type, and 1-1 node alignments (for matches/substitutions).

    Allows customization of insertion, deletion, and substitution costs.
    Passing SUB=-inf indicates that node labels are structured as fixed-length tuples and the substitution cost
    should be computed component-wise, with a cost of 1/N for mismatched elements of length-N tuples:
    e.g., if a node with label ('w', 'x', 'y', 'z') is aligned to a node with
    label ('w', 'x', 'a', 'b'), the component-wise cost is 0 + 0 + 1/4 + 1/4 = 0.5.

    @author: @nschneid
    @since: 2023-05-16
    """
    memo = {}

    nodes1: List[int] = []
    nodes2: List[int] = []
    leftmost1, labels1 = [], []
    leftmost2, labels2 = [], []
    # populate nodes by postorder traversal.
    # labels are what will be compared when two nodes are aligned to determine whether to incur a substitution cost
    # note that any gap antecedent is not included in the label - it will have to be checked after the full alignment is computed by TED
    def _postorder(n: int, T: Tree, result: List[int], leftmosts: List[int], labels: List[tuple]):
        _leftmost = None
        for c in T.children[n]:
            x = _postorder(c, T, result, leftmosts, labels)
            if _leftmost is None:
                _leftmost = x
        if _leftmost is None:
            _leftmost = len(result)
        result.append(n)
        leftmosts.append(_leftmost)
        treenode = T.tokens[n]
        label = (treenode.constituent, treenode.deprel, treenode.lexeme, None)  # pad to length 4 so fractions will be nicer
        labels.append(label)
        return _leftmost

    _postorder(T1.root, T1, nodes1, leftmost1, labels1)
    _postorder(T2.root, T2, nodes2, leftmost2, labels2)
    # leftmost leaf node of the first tree is T1.tokens[nodes[0]]; root is T1.tokens[nodes[-1]]

    def _TED(
        i1: int,    # start index of subforest within T1 (indexes refer to postorder traversal, so bottom-left corner node)
        j1: int,    # end of subforest within T1 (rightmost root node + 1)
        i2: int,    # start of subforest within T2
        j2: int,    # end of subforest within T2
    ) -> Tuple[float,float,float,float,Tuple[Tuple[int,int]]]:    # cost
        hashed = (i1, j1, i2, j2)
        if hashed in memo:
            if DEBUG: print(hashed, memo[hashed], "memo")
            return memo[hashed]

        # Base cases
        if i1==j1 and i2==j2:   # forests are both empty
            return 0, 0, 0, 0, ()
        elif i2==j2: # 2nd forest is empty -> a deletion
            r1 = j1-1   # rightmost root of the T1 subforest
            subcall = _TED(i1, r1, i2, j2)
            return (subcall[0] + DEL, subcall[1], subcall[2]+DEL, subcall[3], subcall[4])
        elif i1==j1: # 1st forest is empty -> an insertion
            r2 = j2-1   # rightmost root of the T2 subforest
            subcall = _TED(i1, j1, i2, r2)
            return (subcall[0] + INS, subcall[1]+INS, subcall[2], subcall[3], subcall[4])

        # Recursive case (both forests are nonempty)
        r1 = j1-1
        r2 = j2-1
        subcall = _TED(i1, r1, i2, j2)  # delete the rightmost tree of the T1 subforest
        ted_DEL = (subcall[0] + DEL, subcall[1], subcall[2]+DEL, subcall[3], subcall[4])
        subcall = _TED(i1, j1, i2, r2)  # insert the rightmost tree of the T2 subforest
        ted_INS = (subcall[0] + INS, subcall[1]+INS, subcall[2], subcall[3], subcall[4])
        # In the source article's notation,
        #    R_k is the subtree rooted at r_k, i.e. T_k[leftmost(r_k)...r_k]
        #    R_k - r_k is T[l(r_k)...r_k-1]
        # If F_k ≠ R_k (the forest doesn’t contain only one tree),
        #    then F_k - R_k is (i, leftmost(r_k)-1). Otherwise, F_k-R_k = {} = T_k[0, 0].
        #  In our 0-based indexing, F_k-R_k spans (i_k, leftmost(r_k)).
        #  If there is only one subtree in the subforest, its lowest-indexed node i_k
        #  will also be its leftmost index, so the span will be equivalent to (i_k, i_k).
        # TED(F1-R1, F2-R2) + cost_rel + TED(R1-r1, R2-r2)
        subcallA = _TED(i1, leftmost1[r1], i2, leftmost2[r2])   # subforests omitting the rightmost tree of each
        subcallB = _TED(leftmost1[r1], r1, leftmost2[r2], r2)   # the rightmost tree

        # cost of aligning rightmost tree roots
        if labels1[r1]==labels2[r2]:
            align_cost = 0
        elif SUB==float('-inf'):
            # component-wise cost
            nComponents = len(labels1[r1])
            align_cost = sum(1/nComponents for l1,l2 in zip(labels1[r1], labels2[r2], strict=True) if l1!=l2)
        else:
            align_cost = SUB

        ted_REL = (subcallA[0] + align_cost + subcallB[0],
                   subcallA[1]+subcallB[1], subcallA[2]+subcallB[2], subcallA[3]+subcallB[3]+align_cost,
                   subcallA[4] + ((r1,r2),) + subcallB[4])
        memo[hashed] = min([ted_DEL, ted_INS, ted_REL])
        # TODO: tiebreaker other than the alignments?

        return memo[hashed]

    cost, INScost, DELcost, SUBcost, offset_alignments = _TED(0, len(nodes1), 0, len(nodes2))
    editcosts = Counter({'INS': INScost, 'DEL': DELcost, 'SUB': SUBcost})
    alignments = {nodes1[i1]: nodes2[i2] for i1,i2 in offset_alignments}
    return cost, editcosts, alignments

def stringify_alignments(alignments: Mapping[int,int], T1: Tree, T2: Tree) -> Tuple[Tuple[str,str]]:
    result = [(f'{n1}:{T1.node_yield(n1, gaps=True)}', f'{n2}:{T2.node_yield(n2, gaps=True)}') for n1,n2 in alignments.items()]
    return tuple(result)


"""
LEVENSHTEIN DISTANCE

Pretty canonical implementation of weighted Levenshtein distance.
"""

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
