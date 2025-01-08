"""
Experimental convertor from CoNLL-2008 dependency parses (covering Penn Treebank WSJ)
to CGEL format.

Data: https://catalog.ldc.upenn.edu/LDC2009T12
Desciption: https://aclanthology.org/W08-2121.pdf

Run as: 
/cgel$ python -m convertor.conll2cgel

In this framework,
- connective function words are heads (including auxiliaries, prepositions, complementizers)
- coordination is done in a chain that includes the conjunction: X-[COORD]->Y-[COORD]->AND-[CONJ]->Z
  for ``X, Y, and Z''
- There are a good number of dependency relations including:
  NMOD = dependent of nominal (incl. determiner, PP, clause -- no modifier/complement distinction),
  AMOD = modifier of adjective,
  PMOD = modifier (object) of preposition,
  ADV = adverbial, TMP = temporal adverbial, SBJ = subject,
  OBJ = verb complement (direct/indirect object or clause), PRD = predicative complement,
  LOC-PRED = locative predicative complement, OPRD = complement of control/raising verb,
  VC = clausal complement of auxiliary.
"""
import sys
sys.path.append('../')
from cgel import Tree as CGELTree
from typing import Literal, Self
from nltk.tree import Tree
from nltk.parse.dependencygraph import DependencyGraph
from nltk.corpus.reader import DependencyCorpusReader



def infer_cgel_pos(dtree: DependencyGraph) -> None:
    for i,node in dtree.nodes.items():
        if i==0: continue
        if node['rel']=='P':    # punctuation
            cpos = ':p'
        else:
            match node['tag']:
                case 'NN'|'NNS'|'NNP'|'NNPS'|'$'|'SYM'|'FW':
                    cpos = 'N'  # TODO: indefinite pronouns
                case 'PRP'|'PRP$'|'WP'|'WP$'|'EX':
                    cpos = 'N_pro'
                case 'CD'|'DT':
                    cpos = 'D'  # TODO: CD can also be N
                case 'PDT':
                    cpos = {'all': 'D', 'both': 'D', 'half': 'D',
                            'many': 'Adj', 'quite': 'Adv'}[node['lemma']]   # TODO: work on this list of predeterminers
                case 'WDT':
                    cpos = 'Sdr' if node['lemma']=='that' else 'N_pro'
                case 'VB'|'VBD'|'VBG'|'VBN'|'VBP'|'VBZ':
                    cpos = 'V_aux' if 'VC' in node['deps'] else 'V'
                case 'MD':
                    cpos = 'V_aux'
                case 'JJ'|'JJR'|'JJS':
                    cpos = 'Adj'
                case 'RB' if node['word'].lower()=="n't":  # negative clitic
                    cpos = ':subt'
                case 'RB'|'RBR'|'RBS'|'WRB':
                    cpos = 'Adv'    # TODO: some actually P
                case 'TO':
                    cpos = 'Sdr'
                case 'IN':
                    if node['lemma'] in ('that','whether'):
                        cpos = 'Sdr'
                    elif node['lemma']=='if' and node['lemma'].rel=='OBJ':
                        cpos = 'Sdr'
                    else:
                        cpos = 'P'
                case 'CC':
                    cpos = 'Coordinator'
                case 'UH':
                    cpos = 'Int'
                case 'POS': # possessive clitic
                    cpos = ':subt'
                case _:
                    assert False,node
        node['cpos'] = cpos # type: ignore

def attach_subtokens(dtree: DependencyGraph) -> None:
    for i,node in dtree.nodes.items():
        if i==0: continue
        if node['cpos']==':subt':    # 's clitic
            prevnode = dtree.nodes[i-1]
            prevnode['subtoks'] = [(':subt', prevnode['word']), (':subt', node['word'])]
            prevnode.setdefault('extra',[]).append('poss')
            prevnode['word'] += node['word']

class T(Tree):
    def __call__(self, fxn: str) -> Self:
        """A copy of this tree with the specified function appended to the category of the root."""
        t = T(self.label()+'-'+fxn, list(self))
        if hasattr(self, '_dnode'):
            t._dnode = self._dnode
        return t

    @property
    def dnode(self) -> dict:
        return self._dnode
    
    @dnode.setter
    def dnode(self, depnode: dict):
        self._dnode = depnode

    @property
    def gapnode(self) -> dict:
        return self._gapnode
    
    @gapnode.setter
    def gapnode(self, depnode: dict):
        self._gapnode = depnode

    @property
    def coidxvar(self) -> str:
        """a.k.a. CGELTree node label - for coindexing gaps and their antecedents"""
        return self._coidxvar
    
    @coidxvar.setter
    def coidxvar(self, var: str):
        self._coidxvar = var

def lex_project(dtree: DependencyGraph) -> list[T]:
    cwords = []
    for i,node in sorted(dtree.nodes.items()):
        if i>0 and node['cpos'] not in (':p',':subt'):
            cpos = node['cpos']
            word = node['word']
            match cpos:
                case 'V'|'V_aux':
                    cword = T('VP', [T(cpos+'-Head', [word])])
                    cword[0].dnode = node
                case 'N_pro':
                    cword = T('NP', [T('Nom-Head', [T(cpos+'-Head', [word])])])
                    cword[0][0].dnode = node
                case 'N':
                    cword = T('Nom', [T(cpos+'-Head', [word])])
                    cword[0].dnode = node
                case 'Adj'|'Adv'|'D'|'Int'|'P':
                    cword = T(cpos+'P', [T(cpos+'-Head', [word])])
                    cword[0].dnode = node
                case 'Coordinator'|'Sdr':
                    cword = T(cpos, [word])
                    cword.dnode = node
            cwords.append(cword)
            node['cproj'] = cword # type: ignore
    return cwords

def is_det_or_poss(dnode: dict) -> bool:
    # for checking on NMOD dependents whether they are candidates for Det function
    # (the first one wins)
    # intentionally omits predeterminers, which are PDT
    xpos = dnode['tag']
    return xpos=='DT' or xpos.endswith('$') or 'poss' in dnode.get('extra',[])

def is_wh_phrase(dtree: DependencyGraph, dnode: dict) -> bool:
    return (dnode['tag'].startswith('W')
            or any(c for c in dnode['deps'].get('PMOD',[]) if dtree.nodes[c]['tag'].startswith('W'))
            or any(c for c in dnode['deps'].get('NMOD',[]) if dtree.nodes[c]['tag'].startswith('W')))

def _move_wh(dtree: DependencyGraph, whnode: dict, parent: dict) -> None:
    whaddr = whnode["address"]
    gapnode = {"address": 1000+whaddr, "word": '--', "lemma": '--',
                "rel": whnode["rel"],
                "tag": None, "cpos": 'GAP', "antecedent": whaddr, "deps": {},
                "cproj": T('GAP', ['--'])}
    gapnode["cproj"].dnode = gapnode
    whnode["rel"] = 'Prenucleus'
    # the projective head is the first verb after the surface position of the WH word
    projectivehead = next(node for a,node in sorted(dtree.nodes.items()) if whaddr<a<1000)
    gapnode["head"] = projectivehead["address"]
    projectivehead["deps"].setdefault('Prenucleus',[]).append(whaddr)
    deps = parent["deps"][gapnode["rel"]]
    deps[deps.index(whaddr)] = gapnode["address"]
    dtree.nodes[gapnode["address"]] = gapnode

def add_gaps(dtree: DependencyGraph, cwords: list[T]):
    """
    Adjust the dependency tree to add gaps reflecting nonprojective or noncanonical word orders.
    Each gap will have the cpos of 'GAP', the word and lemma of '--',
    and an address of 1000 plus its antecedent's address.
    Note that such addresses do not reflect the linear position of the gap relative to words in the sentence.
    """
    for dnode in list(dtree.nodes.values()):
        address: int = dnode['address'] # type: ignore
        if address==0 or address>1000: continue
        cpos = dnode['cpos']
        if cpos==':p': continue
        ordered_deps = list(sorted([(a,rel) for rel in dnode['deps'] for a in dnode['deps'][rel]]))
        if cpos in ('V','V_aux'):
            # canonical order: SBJ on left, nominal-OBJs, then other dependents on right
            if len(dnode['deps']['SBJ'])==1:
                if (caddr := dnode['deps']['SBJ'][0]) > address or dnode['rel']=='NMOD':    # 2nd criterion is for subject relative clauses
                    if is_wh_phrase(dtree,dtree.nodes[caddr]):   # subject WH: move it to prenucleus position
                        _move_wh(dtree, whnode=dtree.nodes[caddr], parent=dnode)
                    elif caddr > address:   # subject-verb inversion: move verb (dnode) to prenucleus position
                        cproj = T(dnode["cpos"], [dnode["word"]])
                        cproj.dnode = dnode
                        lexnode = {"address": 1000+address, "word": dnode["word"], "lemma": dnode["lemma"],
                                   "head": address, "rel": 'Prenucleus',
                                   "tag": dnode["tag"], "deps": {},
                                   "cpos": dnode["cpos"],
                                   "cproj": cproj}
                        dnode["word"] = dnode["lemma"] = "--"
                        dnode["tag"] = None
                        dnode["cpos"] = 'GAP'
                        dnode["antecedent"] = 1000+address
                        dnode["cproj"] = T('VP', [T('GAP-Head', ['--'])])
                        dnode["cproj"][0].dnode = dnode
                        dnode["deps"].setdefault('Prenucleus',[]).append(lexnode["address"])
                        dtree.nodes[lexnode["address"]] = lexnode
            else:
                assert len(dnode['deps']['SBJ'])<=1
            
            for o in dnode['deps']['OBJ']:
                onode = dtree.nodes[o]
                assert address < 1000
                assert o < 1000
                if o < address: # OBJ before verb
                    if is_wh_phrase(dtree,onode):   # move WH word to prenucleus position
                        _move_wh(dtree, whnode=onode, parent=dnode)
                elif ((_o := dnode['deps']['OBJ'].index(o))<len(dnode['deps']['OBJ'])-1 and 
                      not onode["cpos"].startswith(('N','D')) and   # this OBJ is non-nominal
                      any(dtree.nodes[o2]["cpos"].startswith(('N','D')) for o2 in dnode['deps']['OBJ'][_o+1:])):
                    # a non-nominal OBJ precedes a nominal OBJ
                    assert False,'TODO: Postposing?'
            
            # TODO: other kinds of complements/modifiers in clauses

def infer_cgel_function(dtree: DependencyGraph, dchild: dict, dparent: dict) -> str:
    drel = dchild['rel']
    xpos = dchild['tag']
    cpos = dchild['cpos']

    match drel:
        case 'NMOD':
            if is_det_or_poss(dchild) and not any(is_det_or_poss(dtree.nodes[s]) for s in dparent['deps']['NMOD'] if s<dchild['address']):
                # first DT child attaching as NMOD
                return 'Det'
            else:   # modifier of nominal
                return 'Comp' if dchild['lemma']=='of' else 'Mod'
        case 'PMOD':  # object of preposition
            return 'Obj'
        case 'AMOD':  # modifier of adjective
            return 'Mod'
        case 'ADV'|'TMP': # adverbial modifier
            return 'Comp' if dchild['lemma']=='of' else 'Mod'
        case 'SBJ':
            return 'Subj'
        case 'OBJ': # complement of verb
            return 'Obj' if cpos.startswith('N') or cpos=='GAP' and dtree.nodes[dchild["antecedent"]]["cpos"].startswith('N') else 'Comp'
        case 'PRD': # predicative complement
            return 'PredComp'
        case 'VC':  # verb chain (complement of aux)
            return 'Comp'
        case 'COORD'|'CONJ':    # CONJ is the dependent of (coordinate marked by) a CC
            return 'Coordinate'
        case 'DEP' if dchild['cpos']=='Coordinator':
            return 'Marker'
        case _:
            return drel

def build_ctree(dtree: DependencyGraph, dnode: dict) -> T:
    """
    Builds the CGEL tree recursively, working bottom-up from the dependency tree.
    Each subtree is an instance of the `T` class, which extends NLTK's Tree class.
    In the constituent label, the category and function are combined with a hyphen, e.g. `NP-Obj`.
    The function label at the root of a subtree may be omitted at first and
    added when its parent node is processed (via the call syntax).
    """
    result: T = dnode['cproj']
    cat = result.label()

    def _ensure_NP(subtree: T) -> T:
        """Add an NP layer if it is a Nom."""
        if subtree.label()=='Nom':
            return T('NP', [subtree('Head')])
        else:
            assert subtree.label()=='NP'
            return subtree
    
    def _ensure_Clause(subtree: T) -> T:
        """Add a Clause layer if it is a VP."""
        if subtree.label()=='VP':
            return T('Clause', [subtree('Head')])
        else:
            assert subtree.label()=='Clause',subtree
            return subtree

    def _process_child(address, l_or_r: Literal['L','R']):
        nonlocal result, cat
        child_dnode = dtree.nodes[address]
        if child_dnode['cpos'] in (':p',':subt'): return
        child_subtree = build_ctree(dtree, child_dnode) # recurse!
        fxn = infer_cgel_function(dtree, child_dnode, dnode)
        child_cat = child_subtree.label()
        if child_cat=='Nom' and (fxn in ('Subj','Obj','Obj_dir','Obj_ind','Supplement','Det') or fxn=='Mod' and l_or_r=='R'):
            child_subtree = _ensure_NP(child_subtree)
        elif child_cat=='VP' and (fxn not in ('Head','Mod','Coordinate') or fxn=='Mod' and l_or_r=='R'):
            child_subtree = _ensure_Clause(child_subtree)
        
        if child_subtree.label()=='Clause' and child_dnode['tag'] in ('VBD', 'VBP','VBZ') and child_dnode['rel']=='NMOD':
            child_subtree.set_label('Clause_rel')
            if any((clhd := node).label()=='Clause-Head' for node in child_subtree):
                clhd.set_label('Clause_rel-Head')
        child_cat = child_subtree.label()
        
        # TODO: special handling of VP complements, supplements
        if cat=='Sdr':  # in dtree, subordinators are heads of complements
            assert l_or_r=='R'
            result = T(child_cat, [result('Marker'), child_subtree('Head')])
        elif cat=='Coordinator':
            assert l_or_r=='R'
            result = T(child_cat, [result('Marker'), child_subtree('Head')])
        elif fxn=='Coordinate':
            assert l_or_r=='R'
            result = T('Coordination', [result(fxn), child_subtree(fxn)])
        elif fxn=='Subj':
            #assert l_or_r=='L'
            result = T('Clause', [child_subtree('Subj'), result('Head')])
        elif fxn=='Det':
            assert l_or_r=='L'
            result = T('NP', [child_subtree('Det'), result('Head')])
        elif len(result)==1 and isinstance(result[0],T):  # room for a sister without going above binary branching (TODO: don't count supplements)
            if l_or_r=='L':
                result = T(cat, [child_subtree(fxn), result[0]])
            else:
                result = T(cat, [result[0], child_subtree(fxn)])
        else:   # add a layer
            if l_or_r=='L':
                result = T(cat, [child_subtree(fxn), result('Head')])
            else:
                result = T(cat, [result('Head'), child_subtree(fxn)])

        if fxn in ('Prenucleus','Postnucleus'):
            # find a gap that has this constit as antecedent
            gapnode = next(node for node in dtree.nodes.values() if node.get("antecedent")==address)
            # store a pointer to the tree position so that they can be coindexed
            result[{'L': 0, 'R': 1}[l_or_r]].gapnode = gapnode

        if result.label()=='VP':
            if any(node.label()=='Clause-Head' for node in result):
                result.set_label('Clause')
            elif any(node.label()=='Clause_rel-Head' for node in result):
                result.set_label('Clause_rel')

        return result


    address = dnode['address']
    lchildren = []
    rchildren = []
    for drel,children in dnode['deps'].items():
        if drel!='Prenucleus':
            for c in children:
                (lchildren if c<address or drel=='SBJ' else rchildren).append(c)
    # ensure prenucleus is before other dependents
    lchildren = dnode['deps'].get('Prenucleus',[]) + lchildren

    # right-branching analysis
    for c in rchildren:
        _process_child(c, 'R')
    for c in lchildren[::-1]:
        _process_child(c, 'L')

    return result

def build_cgel_tree(targettree: CGELTree, subtree: T, parent: int, dtree: DependencyGraph, antecedents: list[T]):
    if parent==-1:
        cat = subtree.label()
        func = None
    else:
        cat, func = subtree.label().split('-')
    i = len(targettree.tokens)

    #Tree.add_token(self, token: str, deprel: str, constituent: str, i: int, head: int)
    # Called separately for terminal strings vs. non/preterminals
    targettree.add_token(None, func, cat, i, parent)    # proper nodes

    if hasattr(subtree, 'coidxvar'):
        targettree.tokens[i].label = subtree.coidxvar

    for child in subtree:
        if isinstance(child, Tree):
            build_cgel_tree(targettree, child, i, dtree, antecedents)
        else:   # terminal string
            dnode = subtree.dnode
            if targettree.tokens[i].constituent == 'GAP':
                ant = next(t for t in antecedents if t.gapnode is dnode)
                targettree.tokens[i].label = ant.coidxvar
            else:
                targettree.add_token(child, None, None, None, i)
                if dnode['lemma'] != dnode['word']:
                    targettree.tokens[i].lemma = dnode['lemma']
                targettree.tokens[i].xpos = dnode['tag']
                if 'subtoks' in dnode:
                    targettree.tokens[i].substrings = dnode['subtoks']

def attach_punct(tree: CGELTree, sent: list[tuple[str,int]], dtree: dict) -> None:
    """Add punctuation terminals to the CGEL tree given the CGEL-tokenized
    leaves with alignments to the dependency tree nodes."""
    b = 0
    for node in tree.leaves():
        if node.constituent=='GAP': continue
        tok, _ = sent[b]
        while node.text!=tok:
            node.prepunct.append(tok)
            b += 1
            if b==len(sent):
                assert False,(tok,node.text)
            tok, _ = sent[b]
        b += 1
        tok2, a2 = sent[b]
        while (a2 in dtree.nodes and dtree.nodes[a2]['rel']=='P'
               and dtree.nodes[a2]['word'] not in ('``','(','[')):
            node.postpunct.append(tok2)
            b += 1
            if b == len(sent):
                break
            tok2, a2 = sent[b]
    while b < len(sent):
        node.postpunct.append(sent[b][0])
        b += 1



SUBSCRIPT_DIGITS = '₀₁₂₃₄₅₆₇₈₉'
SUPERSCRIPT_DIGITS = '⁰¹²³⁴⁵⁶⁷⁸⁹'

def render_superscript_num(num: int) -> str:
    return ''.join(SUPERSCRIPT_DIGITS[int(c)] for c in str(num))

def convert(dtree: DependencyGraph):
    infer_cgel_pos(dtree)   # store as 'cpos' on each node
    attach_subtokens(dtree) # attach 's to its preceding word
    # TODO: hyphenated words
    cwords = lex_project(dtree) # project phrasal constituent for each lexeme
    sent: list[tuple[str,int]] = [(node['word'],addr) for addr,node in sorted(dtree.nodes.items())[1:] if node['cpos']!=':subt']
    print(' '.join(tok + render_superscript_num(a) for tok,a in sent))

    add_gaps(dtree, cwords)

    assert dtree.root is not None
    ctree = build_ctree(dtree, dtree.root)

    # coindex gaps/antecedents by specifying labels on the T objects
    VARNAMES = 'xyzwabcd'
    antecedents = []
    for i,ant in enumerate(ctree.subtrees(lambda t: hasattr(t,'gapnode'))):
        ant.coidxvar = VARNAMES[i]
        antecedents.append(ant)

    # instantiate CGEL Tree top-down
    tree = CGELTree()
    build_cgel_tree(tree, ctree, -1, dtree, antecedents)

    attach_punct(tree, sent, dtree)

    #assert " ".join(sent)==tree.sentence(gaps=True)

    # TODO: look up gap antecedents and store those in CGELTree
    #print(ctree)
    print(tree)
    print()

def main():
    reader = DependencyCorpusReader('./convertor/', ['wsj-dev-sample-conll2008.conll10'])
    print(reader.sents()[0])
    dtree = reader.parsed_sents()[0]
    print(dtree.root)
    print(dtree.left_children(dtree.root['address']))
    print(dtree.right_children(dtree.root['address']))
    for node in dtree.nodes.values():
        del node['ctag']
    dtree.root['cpos'] = 'V'
    print(dtree.root)
    print('*' * 40)
    print()
    for dtree in reader.parsed_sents():
        convert(dtree)

if __name__=='__main__':
    main()
