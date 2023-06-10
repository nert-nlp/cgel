import sys
sys.path.append('../')
import cgel
from cgel import Tree, Node, trees, Span
from typing import List, Tuple, Mapping

from collections import Counter

"""
Ignoring punctuation
"""

def adjust_lexicalization(ctree: Tree) -> int:
    """
    (0) lexicalization
        split words-with-spaces into flat structures where the first is :Head and others are :Fixed
        split off possessive endings with function :PossClitic
        in a structure with :Compounding dependents, rename the first to :Head and any others to :Mod
    """
    # words with spaces
    for n,node in iter(ctree.tokens.items()):
        if node.lexeme and ' ' in node.lexeme:
            pass    #  TODO: new nodes
    
    # s-possessives
    for n,node in iter(ctree.tokens.items()):
        if node.constituent=='N' and node.lexeme and (node.lexeme.endswith("'s") or node.lexeme.endswith("'")):
            assert node.lexeme.rindex("'")>0
            # TODO: new node
    
    # :Compounding
    for n,node in iter(ctree.tokens.items()):
        if node.deprel=='Compounding':
            cc = ctree.children[node.head]  # n and siblings
            assert not any(c for c in cc if ctree.tokens[c].deprel=='Head')
            cc = [c for c in cc if ctree.tokens[c].deprel=='Compounding']
            ctree.tokens[cc[0]].deprel = 'Head'
            for c in cc[1:]:
                ctree.tokens[cc[0]].deprel = 'Mod'

def relativizers_and_fusion(ctree: Tree):
    """
    (1) pronouns and fusion
        relabel Clause_rel :Marker "that" Sdr->N_pro, :Marker->:Prenucleus and make the antecedent of the gap
        restructure NP :Det-Head (DP :Head X=D) -> NP :Head (Nom :Head X), relabel D->N_pro
        retstructure Nom :Head (Nom :Mod-Head Y) -> Nom :Head (Nom :Head Y) [innocuous extra layer]
        relabel :Marker-Head -> :Head
    """
    for n,node in iter(ctree.tokens.items()):
        if node.constituent=='Sdr' and node.lexeme=='that' and node.deprel=='Marker' and (pnode := ctree.tokens[node.head]).constituent=='Clause_rel':
            # heuristically find the antecedent outside (sibling to) the Clause_rel
            g = pnode.head
            cc = [c for c in ctree.children[g] if ctree.tokens[c].label]
            if len(cc)==1:  # resumptive pronoun case will be 0
                a = cc[0]
                anode = ctree.tokens[a]
                node.label = anode.label
                anode.label = None

                # UD treats "that" as relativizer pronoun heading an NP. Convert to just the NP
                node.deprel = 'Prenucleus'
                node.constituent = 'NP'

        elif node.deprel in ('Det-Head','Mod-Head'):
            node.constituent = 'Nom'
            node.deprel = 'Head'
            cc = [c for c in ctree.children[n] if ctree.tokens[c].deprel=='Head']
            if len(cc)==1:
                h = cc[0]
                hnode = ctree.tokens[h]
                if hnode.constituent=='D':
                    hnode.constituent = 'N_pro' # e.g. demonstrative 'that' as fused determiner-head. pronoun in UD
        
        elif node.deprel=='Marker-Head':
            node.deprel = 'Head'


def remove_gaps(ctree: Tree) -> int:
    """
    (2) remove gaps
        Head-Prenucleus (for fused relatives): convert to just Head, moving the constituent up a level in the tree, 
        and remove the gap.
        Replace other gaps with their antecedents moved from Prenucleus/Postnucleus position. 
        The only antecedents in other functions should be relative clause gap: just remove that gap
        If a Postnucleus consitutent is not coindexed, it indicates an it-cleft; leave it in the tree.
        Check that no other Prenucleus/Postnucleus constituents remain.
    """
    nRemovedGaps = 0
    antecedents = {}
    for n,node in ctree.tokens.items():
        if node.label and node.constituent!='GAP':
            assert node.label not in antecedents
            if node.deprel=='Head-Prenucleus':
                # move up a level in the tree
                p = node.head
                pnode = ctree.tokens[p]
                g = pnode.head
                gnode = ctree.tokens[g]
                ctree.children[p].remove(n)
                node.head = g
                ctree.children[g].insert(ctree.children[g].index(p), n)
                # Head-Prenucleus -> Head
                node.deprel = 'Head'
                # discard this coindexation
                node.label = None
            elif node.deprel in ('Prenucleus', 'Postnucleus'):
                antecedents[node.label] = n
            else:
                # reduced relative antecedents should not substitute for gap
                node.label = None
    # TODO: is it correct to assume sentence order of tokens?
    for n,node in dict(ctree.tokens).items():
        promotion_candidates = None
        if node.constituent=='GAP':
            # remove gap constituent from the tree and replace it by antecedent if possible

            np = ctree.tokens[n].head
            
            if node.label in antecedents:
                a = antecedents[node.label]
                anode = ctree.tokens[a]

                # reassign a's function
                assert anode.deprel in ('Prenucleus', 'Postnucleus'),anode.deprel
                anode.deprel = node.deprel
                
                ap = anode.head
                # n is the gap node, a is the antecedent
                # np, ap are their respective parents
                # (n will be removed from the tree)
                
                # unattach a from ap, reattach it under np
                ctree.children[ap].remove(a)
                anode.head = np
                ctree.children[np].append(a)
                ctree.get_heads()

                # coindexation variable no longer needed
                anode.label = None

                # done with this antecedent
                del antecedents[node.label]
            # else must be a 2nd gap for the antecedent; delete without replacement by antecedent
            elif node.deprel=='Head':
                # the gap that will be deleted is a head
                # since the gap won't be filled in by an antecedent, promote its next sibling to Head
                promotion_candidates = ctree.children[np][ctree.children[np].index(n)+1:] 
                promotion_candidates += ctree.children[np][:ctree.children[np].index(n)]    # in case n is the last sibling
                ctree.tokens[promotion_candidates[0]].deprel = 'Head'

            # delete the gap
            ctree.children[np].remove(n)
            del ctree.tokens[n]
            
            nRemovedGaps += 1

    # Check that only remaining Pre/postnucleus constituents are it-cleft Postnucleus constituents
    assert all((node.deprel=='Postnucleus' and node.label is None) for node in ctree.tokens.values() if 'nucleus' in node.deprel)
    return nRemovedGaps

def flatten_adjuncts(ctree: Tree) -> int:
    """
    (3) flatten adjunct layers
    for any structure of the form (X :Head X), unify the two X constituents
    """
    def _flatten_adjuncts(n: int) -> int:
        "n: node offset; p: its parent's offset"
        node = ctree.tokens[n]
        cc = ctree.children[n]
        if not cc:
            return 0
        
        nMerges = 0
        for c in cc:
            nMerges += _flatten_adjuncts(c)
        hcc = [c for c in cc if ctree.tokens[c].deprel=='Head']
        if len(hcc)==1:
            hc, = hcc
            hcnode = ctree.tokens[hc]
            if node.constituent==hcnode.constituent:
                assert hcnode.lexeme is None
                assert hcnode.label is None
                assert node.label is None,ctree.draw()
                # essentially unify nodes n and c by reattaching all c's children to n
                for chc in ctree.children[hc]:
                    ctree.tokens[chc].head = n
                cc[:] = cc[:cc.index(hc)] + ctree.children[hc] + cc[cc.index(hc)+1:]
                del ctree.tokens[hc]
                ctree.get_heads()
                nMerges += 1
        
        return nMerges

    return _flatten_adjuncts(ctree.root)

def ensure_headedness(ctree: Tree) -> int:
    """
    (4) designate the first element that is a :Coordinate or :Flat dependent as the head
    (and rename Coordination to the first coordinate's category). 
    Also deal with nonce constituents in coordination.
    """
    nChanges = 0
    for n,node in ctree.tokens.items():
        fe = next((c for c in ctree.children[n] if (child := ctree.tokens[c]).deprel in ('Coordinate','Flat')), None)
        firstelt = ctree.tokens[fe] if fe is not None else None
        if firstelt is not None:
            if firstelt.deprel=='Coordinate':
                assert node.constituent=='Coordination',node.constituent
                if '+' in node.deprel:  # nonce function
                    # treat all coordinate parts but the first as belonging in the higher phrase
                    noncedeprel = node.deprel
                    node.deprel = noncedeprel.split('+')[0]
                    nonceconstit = firstelt.constituent
                    firstelt.constituent = nonceconstit.split('+')[0]
                    # designate the first part of the coordinate as the head
                    h = next((c for c in ctree.children[fe] if ctree.tokens[c].deprel==noncedeprel.split('+')[0]), None)
                    ctree.tokens[h].deprel = 'Head'
                    for part in noncedeprel.split('+')[1:]:
                        part = part.split('/')[0]
                        c = next((c for c in ctree.children[fe] if ctree.tokens[c].deprel==part), None)
                        # reattach c to higher phrase (the Coordination as opposed to the nonce phrase)
                        ctree.tokens[c].head = n
                        ctree.children[fe].remove(c)
                        ctree.children[n].append(c)
                # rename Coordination
                node.constituent = firstelt.constituent

            firstelt.deprel = 'Head'
            nChanges += 1

    # remaining (noninitial) coordinates with nonce categories: treat first part as head, rest as orphans
    for n,node in ctree.tokens.items():
        if node.deprel=='Coordinate' and '+' in node.constituent:
            nonceconstit = node.constituent
            node.constituent = nonceconstit.split('+')[0]
            # designate the first non-Marker part of the coordinate as the head
            h = next((c for c in ctree.children[n] if ctree.tokens[c].deprel!='Marker'), None)
            ctree.tokens[h].deprel = 'Head'
            for c in ctree.children[n]:
                if ctree.tokens[c].deprel not in ('Head', 'Marker'):
                    ctree.tokens[c].deprel = 'Orphan'
    
    return nChanges

def add_feats(ctree: Tree, lexheads: Mapping[int,int]) -> Mapping[int,str]:
    """
    (5) decorate clause structure nodes with features

    X=Clause :Head (VP :Head Z=V_aux[lemma=be] :PredComp Y=Clause) => X[+cpred]
    X=Clause :Head (VP :ExtraposedSubj Y) => X[+extra]
    X=Clause :Head (VP :ExtraposedObj Y) => X[+extra]
    X=Clause :Postnucleus Y => X[+cleft]
    VP :Head Z=V_aux[lemma=be] :DisplacedSubj Y => Z[+exist]
    #VP :Head (VP :Head Z=V_aux[lemma=be]) :DisplacedSubj Y => Z[+exist]    # should be flattened
    VP :Head Z=V_aux[lemma=be] :Comp Clause => Z[+aux]
    VP :Head Z=V_aux[lemma=be] :PredComp Y => Z[+cop]
    VP :Head Z=V_aux[lemma=have] :Comp (Clause :Head Y) => Y[+perf]
    VP :Head Z=V[lemma in XCOMP_VERBS] :Comp (Clause :Subj *) => noop
    VP :Head Z=V[lemma in XCOMP_VERBS] :Comp (Clause :Head (VP :Marker Sdr[lemma=to])) => Z[+x]
    VP :Head Z=V[lemma in XCOMP_VERBS] :Comp (Clause :Head (VP :Head V[xpos=VB|VBG|VBN])) => Z[+x]
    # TODO: may need to place further constraints on the +x rules - see Grew queries under XCOMP_VERBS
    """
    feats = {}
    for p,pnode in ctree.tokens.items():
        ph = lexheads[p]
        phnode = ctree.tokens[ph]
        plex = phnode.lemma
        cc = ctree.children[p]
        if pnode.constituent=='Clause':
            vp = phnode.head    # almost always a VP, but there are weird cases of a Clause with no VP
            #assert ctree.tokens[vp].constituent=='VP',ctree.tokens[vp].constituent
            if plex=='be' and phnode.constituent=='V_aux' \
                and any((child := ctree.tokens[c]).deprel=='PredComp' and child.constituent=='Clause' for c in ctree.children[vp]):
                feats[p] = 'cpred'
            elif any(ctree.tokens[c].deprel in ('ExtraposedSubj','ExtraposedObj') for c in ctree.children[vp]):
                feats[p] = 'extra'
            elif any(ctree.tokens[c].deprel=='Postnucleus' for c in cc):
                feats[p] = 'cleft'
        elif pnode.constituent=='VP':
            if plex=='be' and phnode.constituent=='V_aux':
                if any((child := ctree.tokens[c]).deprel=='DisplacedSubj' for c in cc):
                    feats[ph] = 'exist'
                elif any((child := ctree.tokens[c]).deprel=='Comp' and child.constituent=='Clause' for c in cc):
                    feats[ph] = 'aux'
                elif any((child := ctree.tokens[c]).deprel=='PredComp' for c in cc):
                    feats[ph] = 'cop'
            elif plex=='have' and phnode.constituent=='V_aux' and any((child := ctree.tokens[c]).deprel=='Comp' and child.constituent=='Clause' for c in cc):
                # perfect
                comp = next((c for c in cc if (child := ctree.tokens[c]).deprel=='Comp' and child.constituent=='Clause'), None)
                if comp is not None:
                    comph = lexheads[comp]
                    feats[comph] = 'perf'
            elif plex in XCOMP_VERBS:   # check for xcomp
                clcomps = [c for c in cc if (child := ctree.tokens[c]).deprel=='Comp' and child.constituent=='Clause']
                if clcomps:
                    clcomp = clcomps[0]
                    if not any(ctree.tokens[c].deprel=='Subj' for c in ctree.children[clcomp]):
                        vp = next(c for c in ctree.children[clcomp] if ctree.tokens[c].deprel=='Head')
                        if any((child := ctree.tokens[c]).deprel=='Marker' and child.constituent=='Sdr' and child.lemma=='to' for c in ctree.children[vp]):
                            # to-infinitival xcomp
                            feats[ph] = 'x'
                        elif phnode.xpos in ('VB', 'VBG', 'VBN'):
                            # bare nonfinite clause
                            feats[ph] = 'x'
    return feats



XCOMP_VERBS = ['allow','anticipate','ask','attempt','authorise','authorize','begin','believe',
               'come','continue','convince','decide','enjoy','expect','find','forget',
               'get','go','have','hear','help','hesitate','hope','instruct','intend','invite',
               'lead','let','like','look','love','mind','make','mean','need','order',
               'pledge','prefer','promise','propose','recommend','refuse','remain','remember','risk',
               'seem','start','stop','strive','suppose','threaten','try','use','want','watch','wish']
"""Verbs licensing a nonfinite clause xcomp in UD 2.12 EWT dev set (and not tending to license infinitival ccomp).
Infinitival: https://universal.grew.fr/?custom=647bc83a80d1f, https://universal.grew.fr/?custom=647bc95342909
Gerund-Participal: https://universal.grew.fr/?custom=647bcbf20c05b

Note that it's not just to-infinitivals but also "let/help/watch him eat", "used/supposed to eat" etc.
Matches omitted from the list:
- know: "know how to" etc. is not xcomp
- call, see, say: apparent errors
"""

def demote_heads(ctree: Tree, feats: Mapping[int,str]) -> Mapping[int,Tuple[int,str]]:
    """
    (6) head-shifting operations

    * :Head Z=V_aux[cop] :PredComp Y => Y-[cop]->Z
    * :Head Z=V_aux[cop] :Comp Y => Y-[cop]->Z
    * :Head Z=V_aux[exist] => noop
    * :Head Z=V_aux :PredComp Y => Y-[aux*]->Z
    * :Head Z=V_aux :Comp Y => Y-[aux*]->Z

    PP :Head Z=P :Obj Y => Y-[case]->Z
    PP :Head Z=P :Comp Y => Y-[case|mark]->Z
    PP :Head Z=P :PredComp Y => Y-[case]->Z
    ...and convert intransitive P(P) to Adv(P)

    Then, if a Y->Z deprel was added: delete Z from CGEL tree, relabel Y as :Head

    Later, aux* will be renamed to aux or aux:pass
    """

    udeprels = {}
    for n,node in iter(ctree.tokens.items()):
        if node.deprel!='Head':
            continue
        p = node.head
        pnode = ctree.tokens[p]
        cc = ctree.children[p]  # n and its siblings
        
        if node.constituent=='V_aux' and feats.get(n)!='exist':
            if (z := next((c for c in cc if ctree.tokens[c].deprel=='PredComp'), None)) is not None:
                # z -[cop|aux]-> n
                udeprels[n] = (z, 'cop' if feats.get(n)=='cop' else 'aux*') # aux* = aux or aux:pass, TBD in a later stage
            elif (z := next((c for c in cc if ctree.tokens[c].deprel=='Comp'), None)) is not None:
                # z -[cop|aux]-> n
                udeprels[n] = (z, 'cop' if feats.get(n)=='cop' else 'aux*')
            # TODO: aux:pass
        elif node.constituent=='P':
            assert pnode.constituent in ('PP','PP_strand'),pnode.constituent
            z = next((c for c in cc if ctree.tokens[c].deprel=='Obj'), None)
            if z is None:
                z = next((c for c in cc if ctree.tokens[c].deprel=='Comp'), None)
            if z is None:
                z = next((c for c in cc if ctree.tokens[c].deprel=='PredComp'), None)
            
            if z is not None:
                # z -[case]-> n
                udeprels[n] = (z, 'mark' if ctree.tokens[z].constituent=='Clause' else 'case')
                if ctree.tokens[z].constituent=='Clause':
                    pnode.constituent = 'Clause'    # e.g. interested [PP in eating] -> interested [Clause in eating]
            else:
                # intranstive P as :Head. Change it to Adv (AdvP)
                node.constituent = 'Adv'
                pnode.constituent = 'AdvP'
                continue

        # delete n from ctree and relabel z as head
        if n in udeprels:
            z = udeprels[n][0]
            ctree.children[p].remove(n)
            #del ctree.tokens[n]    # we want to be able to look up the lexical head
            znode = ctree.tokens[z]
            znode.deprel = 'Head'
            znode.head = p
            
    return udeprels

def propagate_heads(ctree: Tree) -> Mapping[int,int]:
    """(7) propagate lexical heads via :Head relations"""
    lexheads = {}
    def _propagate_heads(n: int) -> int:
        cc = ctree.children[n]
        for c in cc:
            h = _propagate_heads(c)
            if ctree.tokens[c].deprel=='Head':
                assert n not in lexheads
                lexheads[n] = h
        if not cc:
            lexheads[n] = n
            return n
        assert n in lexheads,'No head found\n' + ctree.draw_rec(n,0)
        return lexheads[n]
    _propagate_heads(ctree.root)
    return lexheads

def mark_passive(ctree: Tree, feats: Mapping[int,str]) -> Mapping[int,str]:
    """
    (8) passive feature

    V[xpos=VBN,perf] => noop
    V[xpos=VBN,cop] => noop
    X=V[xpos=VBN] => X[+pass]
    """
    feats = {**feats}
    for n,node in ctree.tokens.items():
        if node.xpos=='VBN':
            if n in feats:
                assert feats[n] in ('perf','cop'),(feats[n],ctree.draw())
                # N.B. [cop] takes precedence over [perf]: has been[cop] eaten[pass]
            else:
                feats[n] = 'pass'
    return feats

def process_dependents(ctree: Tree, feats: Mapping[int,str], lexheads: Mapping[int,int]) -> Mapping[int,str]:
    """
    (9) head-dependent rules
    """

    RULES_S = """
   |Parent constit     |Parent's head  |Function       |Dep constit    |Dep's head     =>  |Deprel
    -                   -               -               *               *                   root
    *                   *               Orphan          *               *                   orphan
    *                   *               Flat            *               *                   flat
    *                   *               Fixed           *               *                   fixed
    *                   *               PossClitic      *               *                   case
    *                   *               Coordinate      *               *                   conj
    Clause(_rel)[extra] *               Subj            NP              N_pro[it]           expl #limitation: won't capture 'it rained' etc.
    Clause(_rel)[cleft] *               Subj            NP              N_pro[it]           expl
    Clause(_rel)        V_aux[exist]    Subj            NP              N_pro[there]        expl
    Clause(_rel)[cpred] *               Subj            NP              *                   nsubj:outer
    Clause(_rel)[cpred] *               Subj            Clause (!rel)   *                   csubj:outer
    Clause(_rel)        V[pass]         Subj            NP              *                   nsubj:pass
    Clause(_rel)        V[pass]         Subj            Clause (!rel)   *                   csubj:pass
    Clause(_rel)        *               Subj            NP              *                   nsubj
    VP                  *               DisplacedSubj   NP              *                   nsubj
    Clause(_rel)        *               Subj            Clause (!rel)   *                   csubj
    VP                  *               ExtraposedSubj  Clause (!rel)   *                   csubj
    VP                  *               DisplacedSubj   Clause (!rel)   *                   csubj
    VP                  *               Obj_dir         *               *                   obj
    VP                  *               Obj_ind         *               *                   iobj
    VP                  *               Obj             *               *                   obj #limitation: some should be iobj
    AdjP                *               Obj             *               *                   obj
    PP                  *               Obj             *               *                   obj
    VP                  *               PredComp        *               *                   xcomp
    VP                  V[x]            Comp            *               *                   xcomp
    VP                  *               Comp            Clause (!rel)   *                   ccomp
    VP                  *               ExtraposedObj   Clause (!rel)   *                   ccomp
    Clause(_rel)        *               Mod             PP              *                   obl
    VP                  *               Mod             PP              *                   obl
    AdjP                *               Mod             PP              *                   obl
    AdvP                *               Mod             PP              *                   obl
    VP                  *               Comp            PP              *                   obl
    AdjP                *               Comp            PP              *                   obl
    VP                  *               Mod             NP              *                   obl:npmod   #limitation: some should be :tmod
    AdjP                *               Mod             NP              *                   obl:npmod
    AdvP                *               Mod             NP              *                   obl:npmod   # e.g. '11 months later'
    Clause(_rel)        *               *               Clause_rel      *                   advcl:relcl # it-clefts, RC supplements with clausal antecedents
    AdvP                *               *               Clause_rel      *                   advcl:relcl # adverbial fused relative
    PP                  *               *               Clause_rel      *                   advcl:relcl # adverbial fused relative
    Clause(_rel)        *               *               Clause          *                   advcl
    VP                  *               *               Clause          *                   advcl
    AdjP                *               *               Clause          *                   advcl
    *                   *               Comp_ind        Clause (!rel)   *                   advcl
    Clause(_rel)        *               Mod             AdvP            *                   advmod
    VP                  *               Mod             AdvP            *                   advmod
    AdjP                *               Mod             AdvP            *                   advmod
    AdvP                *               Mod             AdvP            *                   advmod
    AdjP                *               Mod             DP              *                   advmod  # e.g. 'enough'
    AdvP                *               Mod             DP              *                   advmod  # e.g. 'a little'
    DP                  *               Mod             DP              *                   advmod  # e.g. 'many more'
    NP                  *               Mod             AdvP            *                   advmod
    PP                  *               Mod             AdvP            *                   advmod
    *                   *               Particle        *               *                   compound:prt
    *                   *               Vocative        *               *                   vocative
    *                   *               *               IntP            *                   discourse
    Clause(_rel)        *               Supplement      AdvP            *                   discourse   # e.g. 'clearly'
    Clause(_rel)        *               Supplement      PP              *                   discourse   # e.g. 'of course'
    *                   *               *               AdvP            *                   discourse
    *                   *               Marker          Coordinator     *                   cc
    *                   *               Marker          DP              *                   cc:preconj
    *                   *               Marker          Sdr             *                   mark
    NP                  *               Mod             DP              *                   det:predet
    NP                  *               Mod             AdjP            *                   det:predet  # exclamative 'what'
    *                   *               Det             DP              D[xpos=CD]          nummod
    Nom                 *               Mod             DP              D[xpos=CD]          nummod
    *                   *               Det             DP              *                   det
    *                   *               Det             NP              *                   nmod:poss
    *                   *               Det             *               *                   amod
    Nom                 *               Mod             AdjP            *                   amod
    Nom                 *               Mod             VP              *                   amod
    Nom                 *               Mod             DP              *                   amod    # e.g. 'many'
    Nom                 *               Mod             Nom             *                   compound
    Nom                 *               Mod             Clause_rel      *                   acl:relcl
    Nom                 *               Supplement      Clause_rel      *                   acl:relcl
    NP                  *               Supplement      Clause_rel      *                   acl:relcl
    Nom                 *               Mod             Clause          *                   acl
    Nom                 *               Comp            Clause          *                   acl
    Nom                 *               Mod             PP              *                   nmod    # TODO: ignoring :npmod, :tmod possibilities
    Nom                 *               Comp            PP              *                   nmod
    NP                  *               Supplement      NP              *                   appos
    *                   *               Supplement      *               *                   parataxis
    """
    # TODO: list, dislocated, reparandum?

    def meets_constraint(val: str | Node, feat: str | None, constraint: str):
        if constraint=='*' or val==constraint:
            return True
        elif constraint=='-':
            return not val
        elif constraint=='Clause(_rel)':
            return val in ('Clause', 'Clause_rel')
        elif constraint=='Clause(_rel)[extra]':
           return val in ('Clause', 'Clause_rel') and feat=='extra'
        elif constraint=='Clause(_rel)[cleft]':
           return val in ('Clause', 'Clause_rel') and feat=='cleft'
        elif constraint=='Clause(_rel)[cpred]':
           return val in ('Clause', 'Clause_rel') and feat=='cpred'
        elif constraint=='Clause (!rel)':
            assert val!='Clause_rel'
            return val=='Clause'
        elif constraint=='V_aux[exist]':
            return val.constituent=='V_aux' and feat=='exist'
        elif constraint=='V[x]':
            return val.constituent=='V' and feat=='x'
        elif constraint=='V[pass]':
            return val.constituent=='V' and feat=='pass'
        elif constraint=='N_pro[it]':
            return val.constituent=='N_pro' and val.lemma=='it'
        elif constraint=='N_pro[there]':
            return val.constituent=='N_pro' and val.lemma=='there'
        elif constraint=='D[xpos=CD]':
            return val.constituent=='D' and val.xpos=='CD'
        elif '[' in constraint:
            assert False,'Unknown constraint: ' + constraint
        return False

    # Load rules from string
    HEADER = RULES_S.splitlines()[1]
    column_starts = [i+1 for i,c in enumerate(HEADER) if c=='|']
    RULE_LINES = RULES_S.splitlines()[2:-1]
    RULES = []
    for ln in RULE_LINES:
        rule = []
        for c,j in enumerate(column_starts):
            if c>0:
                rule.append(ln[column_starts[c-1]:j].strip())
        rule.append(ln[column_starts[-1]:].strip())
        if '#' in (r := rule[-1]):  # strip off comment
            rule[-1] = r[:r.index('#')].strip()
        RULES.append(rule)
    
    udeprels = {}

    # Traverse the tree bottom-up. For each node, process rules in order.
    def _process_dependents(n: int):
        cc = ctree.children[n]
        for c in cc:
            _process_dependents(c)
        node = ctree.tokens[n]
        if node.deprel=='Head':
            return
        ncat = node.constituent
        nfxn = node.deprel
        nlex = ctree.tokens[lexheads[n]]
        p = node.head
        if p==-1:
            pnode = pcat = plex = pfeat = plexfeat = None
        else:
            pnode = ctree.tokens[p]
            pcat = pnode.constituent
            pfeat = feats.get(p)
            plex = ctree.tokens[lexheads[p]]
            plexfeat = feats.get(lexheads[p])

        # rule specifications
        for rule in RULES:
            Pcat, Plex, Nfxn, Ncat, Nlex, Result = rule
            #if Nlex=='N_pro[there]' and nlex.constituent=='N_pro' and nlex.lemma=='there':
            #    assert False,(plex.lemma,plex.constituent,pfeat,plexfeat,(plex,plexfeat,Plex),meets_constraint(plex,plexfeat,Plex))
            if all(meets_constraint(val, feat, constraint) for val,feat,constraint in [(pcat,pfeat,Pcat),(plex,plexfeat,Plex),(nfxn,None,Nfxn),(ncat,None,Ncat),(nlex,None,Nlex)]):
                if plex is None:
                    udeprels[n] = f'{Result}({nlex.lexeme})'
                else:
                    udeprels[n] = f'{Result}({plex.lexeme}, {nlex.lexeme})'
                return
        assert n in udeprels,(pcat,plex,nfxn,ncat,nlex,ctree.draw_rec(n,0))
    
    _process_dependents(ctree.root)
    return udeprels
        







def convert(ctree: Tree):
    #print(ctree.draw())
    origS = ctree.draw()
    adjust_lexicalization(ctree)
    relativizers_and_fusion(ctree)
    nGapsRemoved = remove_gaps(ctree)
    nMerges = flatten_adjuncts(ctree)
    nHeadChanges = ensure_headedness(ctree)
    #print(ctree)
    lexheads0 = propagate_heads(ctree)
    feats = add_feats(ctree, lexheads0)
    udeprels0 = demote_heads(ctree, feats)
    lexheads = propagate_heads(ctree)
    feats = mark_passive(ctree, feats)
    udeprels = {}
    passive_aux_marked = set()
    for n,(h,rel) in sorted(udeprels0.items(), reverse=True):   # RTL so we mark the rightmost aux dep of a passive verb as aux:pass, others as plain aux
        if rel=='aux*':
            if lexheads[h] in passive_aux_marked:
                rel = 'aux'
            elif feats.get(lexheads[h])=='pass':
                rel = 'aux:pass'
                passive_aux_marked.add(lexheads[h])
            else:
                rel = 'aux'
        udeprels[n] = f'{rel}({ctree.tokens[lexheads[h]].lexeme}, {ctree.tokens[lexheads0[n]].lexeme})'
    # note that for the function word dependent we have to use lexheads0[n] following CGEL headedness as opposed to UD headedness
    udeprels |= process_dependents(ctree, feats, lexheads)
    finalS = ctree.draw()
    #print(ctree.draw())
    # print(nGapsRemoved, 'gaps removed; ', nMerges, 'merges', nHeadChanges, 'head changes')
    # if nGapsRemoved>0:
    #     print(origS)
    #     print(ctree.draw())
    print(udeprels.values())
    print(feats)
    # if 'whether' in finalS:
    #     print(finalS)
    #     assert False


inFP = 'twitter.xpos.cgel'
with open(inFP) as inF:
    for tree in cgel.trees(inF):
        convert(tree)
        #assert False

