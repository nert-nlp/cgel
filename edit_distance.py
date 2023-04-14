from cgel import Tree, trees, Span
from typing import List, Tuple, Mapping

DEBUG = False

"""
TREE EDIT DISTANCE

The following implementation of tree edit distance is based on the recursive algorithm
described in Pawlik and Augsten (2012): https://dl.acm.org/doi/pdf/10.14778/2095686.2095692.

This is not optimised for space, it's the simplest memoised implementation.
"""

def tree_edit_distance(F: Tree, G: Tree) -> int:
    return ted(F, G, [F.root], [G.root], 1, 1, 1, {})
    
def ted(
    F: Tree,
    G: Tree,
    roots_F: List[int],
    roots_G: List[int],
    ins: int,
    dlt: int,
    sub: int,
    memo: dict = {},
) -> int:
    hashed = (tuple(roots_F), tuple(roots_G))
    if hashed in memo:
        if DEBUG: print(hashed, memo[hashed], "memo")
        return memo[hashed]
    
    if len(roots_F) == 0 and len(roots_G) == 0: # base case: both trees are empty, so 0 cost
        memo[hashed] = 0
    
    elif len(roots_G) == 0: # delete root incrementally if one tree is empty
        v = roots_F[0]
        new_roots_F = F.children[v] + roots_F[1:]
        memo[hashed] = dlt + ted(F, G, new_roots_F, roots_G, ins, dlt, sub, memo)
    
    elif len(roots_F) == 0:
        w = roots_G[0]
        new_roots_G = G.children[w] + roots_G[1:]
        memo[hashed] = ins + ted(F, G, roots_F, new_roots_G, ins, dlt, sub, memo)
    
    elif len(roots_F) > 1 or len(roots_G) > 1: # if both have multiple roots (i.e. are forests)
        v = roots_F[0]
        w = roots_G[0]
        new_roots_F = F.children[v] + roots_F[1:]
        new_roots_G = G.children[w] + roots_G[1:]
        memo[hashed] = min(
            dlt + ted(F, G, new_roots_F, roots_G, ins, dlt, sub, memo),
            ins + ted(F, G, roots_F, new_roots_G, ins, dlt, sub, memo),
            ted(F, G, [v], [w], ins, dlt, sub, memo) + ted(F, G, roots_F[1:], roots_G[1:], ins, dlt, sub, memo),
        )
    
    else: # both are trees
        v = roots_F[0]
        w = roots_G[0]
        new_roots_F = F.children[v] + roots_F[1:]
        new_roots_G = G.children[w] + roots_G[1:]
        sub_cost = 0 if (F.tokens[v].constituent == G.tokens[w].constituent and F.tokens[v].deprel == G.tokens[w].deprel) else sub
        if DEBUG: print(f"COMPARE `{F.tokens[v]}` `{G.tokens[w]}`", sub_cost)
        memo[hashed] = min(
            dlt + ted(F, G, new_roots_F, roots_G, ins, dlt, sub, memo),
            ins + ted(F, G, roots_F, new_roots_G, ins, dlt, sub, memo),
            sub_cost + ted(F, G, new_roots_F, new_roots_G, ins, dlt, sub, memo),
        )

    if DEBUG: print(hashed, memo[hashed], "new")
    return memo[hashed]

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