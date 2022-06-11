#!/usr/bin/env python3
"""
Script to heuristically infer CGEL clause type features in UD trees
as specified [here](datasets/twitter_parsed/README.md#clause-types).

Currently set up to evaluate the heuristics against the gold annotations
in the Twitter data. Just run this script directly with no arguments.

@author: Nathan Schneider (@nschneid)
@since: 2022-06-11
"""

import conllu, math

def first_child(node, deprels):
    for c in node.children:
        if c.token['deprel'] in deprels:
            return c
    return None

def subtree_yield(node, omit_punct=False):
    toks = [node.token] if (not omit_punct) or node.token['deprel']!='punct' else []
    for c in node.children:
        toks.extend(subtree_yield(c))
    return sorted(toks, key=lambda t: t['id'])

def has_exclamative_prefix(node):
    """Is this a 'what a' exclamative?"""
    yy = subtree_yield(node, omit_punct=True)
    w1,w2 = (yy[:2] + [None, None])[:2]
    if w1 and w1['lemma']=='what' and w2 and w2['lemma']=='a':
        return True
    return False

def looks_exclamative(node):
    """
    Determine whether the context suggests this is a how-exclamative
    (since word order is ambiguous with interrogative).

    Selected verbs and adjectives that can be factive and license how-exclamatives
    (informed by CGEL pp. 958, 978, 1008):
      - acknowledge, accept, believe, prove, realise, realize, resent
      - amuse, annoy, bother, disturb, delight, frighten, frustrate, irritate, offend, scare
      - amazing, exciting, incredible, odd, outrageous, surprising, tragic, unfair, unusual
      - affirmative “how” complement tends to be exlamative; negative “how” complement may be interrogative:
          indicate, notice, observe, recall, remember
    Exception: “how (not) to”
    """
    yy = subtree_yield(node, omit_punct=True)
    yy = (yy[:3] + [None, None, None])[:3]
    w1,w2,w3 = [y['lemma'] if y else None for y in yy]
    if w1!="how" or (w1,w2)==("how","to") or (w1,w2,w3)==("how","not","to"):
        return False
    VERBS = {'acknowledge', 'accept', 'believe', 'prove', 'realise', 'realize', 'resent',
             'amuse', 'annoy', 'bother', 'disturb', 'delight', 'frighten', 'frustrate',
             'irritate', 'offend', 'scare'}
    VERBS2 = {'indicate', 'notice', 'observe', 'recall', 'remember'}
    ADJS = {'amazing', 'exciting', 'incredible', 'odd', 'outrageous', 'surprising', 'strange',
            'tragic', 'unfair', 'unusual', 'weird'}
    if node.token['deprel'] in ('ccomp','csubj','csubj:pass'):
        if (node.head.token['upostag']=='VERB' and node.head.token['lemma'] in VERBS or
            node.head.token['upostag']=='ADJ' and node.head.token['lemma'] in ADJS):
            return True
        elif node.head.token['upostag']=='VERB' and node.head.token['lemma'] in VERBS2:
            # check for negation
            for c in node.children:
                if c.token['deprel']=='advmod' and c.token['lemma']=='not':
                    return False  # likely interrogative: "I don't recall how many books I read"
            return True
    return False

def has_lemma_prefix(node, words):
    yy = subtree_yield(node, omit_punct=True)
    if len(words)>len(yy):
        return False
    return [y['lemma'] for y in yy[:len(words)]]==words

def extract_clause_feats(node, wh):
    """
    Assuming node is the root of a clause, returns which clause-level features should apply.

    'wh' indicates whether there is a WH-word within this clause (and no intermediate clause).
    """
    main = False
    rel = False
    interrog = False
    excl = False
    exist = False
    imper = False
    compar = False

    d = node.token['deprel']
    subj = first_child(node, {'nsubj', 'nsubj:pass', 'csubj', 'csubj:pass', 'expl'}) # TODO: outer vs. inner clauses

    if d in ('root','parataxis','discourse'):
        main = True
    elif d=='acl:relcl':
        rel = True
    elif d in ('conj','ccomp','xcomp','csubj','csubj:pass') and any(c.token['xpostag'] in ('``', "''") for c in node.children):
        # direct quotations
        main = True
    elif d=='conj': # check for local subject. V coordination and VP coordination are not treated as multiple clauses
        if subj:
            # Find the nearest ancestor that doens't attach as conj, and determine whether it's a main clause
            h = node.head
            while h.token['deprel']=='conj':
                h = node.head
            if h.token['deprel'] in ('root','parataxis','discourse'):
                main = True
            elif h.token['deprel']=='acl:relcl':
                rel = True
        else:  # don't consider this a clause
            return {}

    mark = first_child(node, {'mark'})
    m = mark.token['lemma'] if mark else None
    #if mark.token['lemma']=='that':
    #if m=='to' and mark.token['upostag']=='PART':  # there are also bare infinitivals
    #    finite = 'Inf'
    #else:
    tense_bearer = first_child(node, {'cop', 'aux', 'aux:pass'}) or node
    vf = tense_bearer.token['feats'] and tense_bearer.token['feats'].get('VerbForm')
    assert vf in ('Fin','Part','Ger','Inf'),(vf,tense_bearer.token)
    finite = 'Part' if vf=='Ger' else vf
    mood = tense_bearer.token['feats'] and tense_bearer.token['feats'].get('Mood')
    assert mood in ('Ind','Imp',None),mood
    if mood=='Imp':
        imper = True


    if m=='if':
        interrog = 'ClosedInt' if d=='ccomp' else False
    elif m=='whether':
        interrog = 'ClosedInt'
    elif m in ('than', 'as'):
        compar = 'Compar'
    elif m=='like':
        compar = 'Compar?'  # ambiguous with content clause, needs manual check

    if has_exclamative_prefix(node):  # "what a" exclamative
        excl = True
    elif wh < node.token['id'] and not rel and d not in {'advcl','acl'}:
        # a WH word descendant to the left that is not part of an intermediate clause
        # (descendant, not necessarily child: What big ears you have!, Whose books are those?, How much money do you make?)
        # Adjunct clauses like "When he was a boy (he chopped down a cherry tree)" are not included--
        # unfortunately we have no way to tell whether acl is an adjunct or complement of a noun.

        aux = first_child(node, {'cop', 'aux', 'aux:pass'})
        subj = first_child(node, {'nsubj', 'nsubj:pass', 'csubj', 'csubj:pass', 'expl'}) # TODO: outer vs. inner clauses
        if main and aux and subj and aux.token['id']>subj.token['id']:  # No Inversion!
            excl = True
            # Restricted to main clauses: subordinate exclamatives are usually ambiguous with open interrogatives :(
        elif looks_exclamative(node):
            # Context suggests a how-exclamative
            # (subordinate what-exclamatives that do not start with "what a" are rare)
            excl = True
        else:
            assert interrog==False
            interrog = 'OpenInt'
    else: # check for SAI that would indicate a main clause closed interrogative
        aux = first_child(node, {'cop', 'aux', 'aux:pass'})
        subj = first_child(node, {'nsubj', 'nsubj:pass', 'csubj', 'csubj:pass', 'expl'}) # TODO: outer vs. inner clauses
        if aux and subj and aux.token['id']<subj.token['id']:  # Inversion!
            interrog = 'ClosedInt'

    expl = first_child(node, {'expl'})
    if expl and expl.token['lemma']=='there' and node.token['lemma']=='be':
        exist = True

    result = {}
    if exist:
        result['Exist']='Yes'

    result['ClauseLevel'] = 'Main' if main else 'Sub'

    if finite=='Fin':
        result['ClauseFinite']='Yes'
    elif finite: # Inf or Part
        if finite=='Inf' and rel:
            result['ClauseType']='Inf,Rel'
        else:
            result['ClauseType']=finite
            if main or excl or interrog or rel or imper or compar: #(finite,main,excl,interrog,rel,imper)
                # Something weird here, maybe it's a fragment or something
                result['ClauseType'] += '?'

    if 'ClauseType' not in result:
        assert excl + bool(interrog) + rel + imper + bool(compar) <= 1,(excl,interrog,rel,imper,compar,node.token)
        result['ClauseType'] = ('Excl' if excl else interrog if interrog else compar if compar else 'Rel' if rel else 'Imp' if imper else 'Decl')
        if finite=='Fin' and not main and not rel and not compar:
            assert not imper,(node.token,(finite,main,excl,interrog,rel,imper))
            result['ClauseType'] = 'Content,' + result['ClauseType']

    if main and not imper and not subj:
        result['ClauseType'] += ',Frag'

    return result

def add_clause_feats(node):
    """
    Recursively find nodes that project clauses and infer clause-level features.
    Features are added to the MISC part of the token.

    If the subtree of the node (clause or otherwise)
    contains a WH word (PronType=Int) that is not part of a lower clause,
    returns the ID of the first such WH word.
    This value defaults to infinity meaning no WH word.
    """
    wh = math.inf
    for c in node.children:
        c.head = node
        wh = min(wh, add_clause_feats(c))

    """
    Is this a clause?
    Heuristic: treat as a clause iff node
    1) has a subject, cop, or aux dependent, or
    2) is a VERB with deprel other than {case, mark, amod, compound, flat, fixed, reparandum}
    subject to
    3) does not attach as conj without a local subject

    or

    4) is the sentence root and begins with "how" or "what a": verbless exclamative (finite 'be' verb implied)
    Note that AUXes are NOT considered to project their own clause by this definition.
    In a copular construction, the predicate is marked as projecting the clause.
    """
    # TODO: revisit VERB/compound (e.g. a check-in operation)
    # TODO: maybe include mark in (1). http://universal.grew.fr/?custom=62a3b9bf385fe
    # TODO: predicate clauses, e.g. :outer subject

    d = node.token['deprel']

    # criteria (1), (2)
    i_am_santa = bool((node.token['upostag']=='VERB' and d not in {'case','mark','amod','compound','flat','fixed','reparandum'})
        or first_child(node, {'aux','aux:pass','cop','nsubj','nsubj:pass','csubj','csubj:pass','expl'})) # TODO: :outer
    # exception (3): subjectless noninitial conjunct will be handled by extract_clause_feats()

    result = None
    if i_am_santa or d=='root':  # this is a clause (or the root which should always be considered a likely clause)
        if i_am_santa:
            result = extract_clause_feats(node, wh)
            if not result:
                i_am_santa = False
        else:  # root
            if (has_lemma_prefix(node, ["how"]) or has_lemma_prefix(node, ["what","a"])): # criterion (4): verbless exlamatives
                i_am_santa = True
                result = {'ClauseType': 'Excl', 'ClauseFinite': 'Yes', 'ClauseLevel': 'Main'}
            elif node.token['upostag'] in ('ADJ','ADV') or first_child(node, {'mark', 'case'}):
                i_am_santa = True
                result = {'ClauseType': '?', 'ClauseLevel': 'Main', 'ClauseFinite': '?'}
            else: # default to assuming the sentence is not a clause. a couple false negatives that are Decl,Frag
                i_am_santa = False
                result = {}

    if i_am_santa:
        wh = math.inf
    elif node.token['feats'] and node.token['feats'].get('PronType')=='Int':
        wh = min(wh, node.token['id'])

    assert i_am_santa==bool(result and 'ClauseType' in result),(i_am_santa,result)

    # Evaluate result against gold annotations in node.token['misc']

    global nClCorrect, nClUnsure, nClWrong
    if i_am_santa:
        if first_child(node, {'nsubj:outer','csubj:outer'}):
            print('Skipping predicate because it has an :outer subject and thus projects multiple clauses', node.token)
            nClUnsure += 1
        else:
            unsure = False
            errors = False
            for k,v in result.items():
                goldv = node.token['misc'].get(k)
                if '?' in v:
                    unsure = True
                if goldv!=v:
                    errors = True
                    print(goldv==v, k, v, node.token['misc'].get(k), node.token)
                if k=='ClauseType' and goldv!=v: # debug these subcases:
                    if {goldv, v} < {None, 'Part', 'Inf', 'Imp', 'Decl', 'ClosedInt', 'OpenInt', 'Content,Excl', 'Content,Decl', 'Content,OpenInt'}:
                        print(result,node.token)
            if not result:
                if 'ClauseType' in node.token['misc']:
                    errors = True

            if unsure:
                nClUnsure += 1
            elif errors:
                nClWrong += 1
            else:
                for k in {'ClauseType','ClauseLevel','ClauseFinite','Exist'}:
                    if k not in result:
                        assert k not in node.token['misc'],(k,result)
                nClCorrect += 1
    else:
        if node.token['misc'] and 'ClauseType' in node.token['misc']:
            nClWrong += 1  # false negative
            print(node.token['misc'])

    return wh

if __name__=='__main__':
    # Evaluate gold Twitter annotations
    nClCorrect = nClUnsure = nClWrong = 0
    with open('datasets/twitter_parsed/sentences_fixed.conllu',encoding='utf-8') as inF:
        i = 0
        for tree in conllu.parse_tree_incr(inF):
            i += 1
            if i==2: continue # TODO: s2 isn't done yet
            add_clause_feats(tree)
            print()
    print(f'''Clauses Correct: {nClCorrect}
        Unsure or skipped: {nClUnsure} ({nClUnsure/(nClUnsure+nClCorrect+nClWrong):0.1%})
        Incorrect (incl. FP or FN): {nClWrong} ({nClWrong/(nClUnsure+nClCorrect+nClWrong):0.1%})''')
