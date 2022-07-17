import conllu
import sys
sys.path.append('../')
import cgel
from cgel import Node
from collections import Counter
from math import log
from difflib import get_close_matches

ADD_PUNCT_AND_SUBTOKS = False
INFER_VAUX = False
INFER_LEMMA = True

with open('../datasets/twitter_ud.conllu') as f, open('../datasets/ewt_ud.conllu') as f2:
    ud_trees = conllu.parse( #f.read() +
        f.read())

cgel_trees = []
with open('../datasets/twitter.cgel') as f, open('../datasets/ewt.cgel') as f2:
    for tree in cgel.trees(f):
        cgel_trees.append(tree)

def ud_tok_scanner(ud_tree):
    for node in ud_tree:
        if isinstance(node['id'], int): # skip token ranges
            yield node

def insert_subtoken(cgel_node: Node, subtoken: str):    # lexical material that is tokenized more aggressively in UD than CGEL
    if ADD_PUNCT_AND_SUBTOKS:
        cgel_node.substrings = (cgel_node.substrings or []) + [(':subt', subtoken)]

def insert_subpunct(cgel_node: Node, punct: str):    # UD-segmented punctuation within a lexical item (e.g. hyphen)
    if ADD_PUNCT_AND_SUBTOKS:
        cgel_node.substrings = (cgel_node.substrings or []) + [(':subp', punct)]

def insert_prepunct(cgel_node: Node, punct: str):
    if ADD_PUNCT_AND_SUBTOKS:
        cgel_node.prepunct += (punct,)

def insert_postpunct(cgel_node: Node, punct: str):
    if ADD_PUNCT_AND_SUBTOKS:
        cgel_node.postpunct += (punct,)


""" AUX lemmas in all of EWT:
  10851 be
   1017 can
    431 could
   1430 do
     70 get ** NOT A CGEL V_aux: The city got destroyed -> did not get destoryed/*got not destroyed; Did the city get destroyed?/*Got the city destroyed?
   1984 have
    244 may
    109 might
    101 must
      2 ought
     35 shall
    345 should
   1472 will
   1006 would

EWT Manually changed:
Retag as V_aux?  is | not that there is anything wrong with that because they also employ local people that that live and shop in the area
Retag as V_aux?  is | you should give her a try it 's worth every penny to know that you pet is in great hands with Wunderbar pet sitting
Retag as V_aux? are | but there are strong hints in the country that a new Indo - Sri Lanka defense deal could be in the making
Retag as V_aux?  is | this person is not coming to visit you the whole point of this scam is to gain your trust enough to steal your money and identity
Retag as V_aux?  's | he doesn't just take pictures he makes art out of them and you won't even notice that there 's a camera there

EWT Manually changed, UD still out of date:
Retag as V_aux?  is | what we are trying to do is solicit votes for the band in order to put them in first place
"""
AUX_LEMMAS = {'be','can','could','do','have','may','might','must','ought','shall','should','will','would'}

# (CGEL,EWT)
#EWT_MISTRANSCRIPTIONS = {("200","200,000"),("San","Sao"),("Grill","Grille"),("investigators","interrogators"),
#    ("favour","favor"),("issues","issue"),("trouble","problems"),("sushi","sashimi"),("sashimi","sushi"),
#    ("lawyers","politicians"),("politicians","lawyers")}
EWT_MISTRANSCRIPTIONS = set()
#EWT_SPELLING_CORRECTIONS_IN_CGEL = {("lose","Loose"),("billings","Billing"),("schedule","scheduled")}
EWT_SPELLING_CORRECTIONS_IN_CGEL = set()

gaps = set()

assert len(ud_trees)==len(cgel_trees)
iSent = 0
for ud_tree,cgel_tree in zip(ud_trees,cgel_trees):
    iSent += 1
    cgel_sentid = cgel_tree.sentid
    cgel_sent = cgel_tree.sent
    cgel_toks = [node for node in cgel_tree.tokens.values() if node.text or node.constituent=='GAP']
    udnI = ud_tok_scanner(ud_tree)
    udn = None
    last_nongap = None
    for n in cgel_toks:
        if n.constituent=='GAP':
            sentid = cgel_sentid
            gapij = f'{udn["id"] if udn else 0}/{udn["id"]+1 if udn else 1}'
            gaps.add((sentid, gapij))
            continue
        last_nongap = n
        buf = n.text
        #buf = buf.replace("''", '"') # "clitic" sentence
        udn = next(udnI,None)
        if udn is None:
            assert False,('UD: EOS',cgel_sentid)
        while not buf.lower().startswith(udn['form'].lower()) and (buf,udn['form']) not in EWT_MISTRANSCRIPTIONS | EWT_SPELLING_CORRECTIONS_IN_CGEL:
            if udn['deprel']=='punct':
                insert_prepunct(n, udn['form'])
                #print('UD punct:', udn['form'])
            else:
                assert False,f'UD-only word: {udn["form"]:10} #' + cgel_sentid.rsplit('/')[-1].split('.')[0] + ' ' + cgel_tree.sentence()

            udn = next(udnI, None)
            if udn is None:
                assert False,('UD: EOS',cgel_sentid)
                break
        assert n.correct==(udn.get('misc') or {}).get('CorrectForm'),(n.correct,(udn.get('misc') or {}).get('CorrectForm'))

        if INFER_VAUX:
            if udn['upos']=='AUX':
                if udn['lemma']!='get':    # get is not a CGEL Vaux
                    assert udn['lemma'] in AUX_LEMMAS,n.text
                    assert n.constituent in ('V', 'V_aux'),n
                    n.constituent = 'V_aux'
            elif udn['upos']=='VERB' and udn['lemma'] in AUX_LEMMAS:
                assert n.constituent in ('V', 'V_aux'),n.constituent
                if n.constituent=='V':
                    print('Retag as V_aux?', n.text, cgel_tree.sentence(), file=sys.stderr)

        if INFER_LEMMA:
            t = (n.text or n.correct)
            if udn['lemma']!=buf:
                if udn['lemma'].lower()==t.lower():
                    print(udn['lemma'],t, file=sys.stderr)
                n.lemma = udn['lemma']
                # if not explicitly set, the lemma defaults to the token form

        #print(buf)
        assert udn
        if len(buf)==len(udn['form']): # or (buf,udn['form']) in {("if'","If"), ("of'","of")} | EWT_MISTRANSCRIPTIONS | EWT_SPELLING_CORRECTIONS_IN_CGEL:
            continue
        while buf:
            if not buf.lower().startswith(udn['form'].lower()) and (buf,udn['form']) not in {("n't", 'n’t')}:
                if buf.startswith('-') and not udn['form'].startswith('-'):
                    #print('CGEL-only subpart: -')
                    buf = buf[1:]
                    continue
                assert udn['form']=='-',(cgel_sentid,buf,udn['form'])
                #print('UD infix:', udn['form'])
                insert_subpunct(n, udn['form'])
            else:
                #print('UD subtok:', udn['form'])
                insert_subtoken(n, udn['form'])
                buf = buf[len(udn['form']):]
            if buf and buf[0]==' ':
                buf = buf[1:]
            if buf:
                # We've matched part of buf but there is more (multiple corresponding UD nodes). grab the next one
                udn = next(udnI)

    # n is the last CGEL token. insert any subsequent UD stuff
    while udn:
        udn = next(udnI, None)
        if udn is None: continue
        assert udn['deprel']=='punct',udn
        insert_postpunct(last_nongap, udn['form'])


    # Print the metadata and tree (with any modifications)
    s = cgel_tree.sentence(gaps=True)
    if s!=cgel_sent:
        print('MISMATCH:', s,'||',cgel_sent, file=sys.stderr)
    print('# sent_id =', cgel_tree.sentid)
    print('# sent_num =', cgel_tree.sentnum)
    if 'alias' in cgel_tree.metadata:
        print('# alias =', cgel_tree.metadata['alias'])
    print('# text =', cgel_tree.text)
    print('# sent =', cgel_sent)
    print(cgel_tree.draw())
    print()


#print(gaps, file=sys.stderr)
"""
cgel_tree.tokens[70] = cgel.Node(deprel="Extra",constituent="X",head=3,text="extraextra")
cgel_tree.children[3].append(70)
#cgel_tree.add_token(token="extraextra",deprel="Extra",constituent="X",i=70,head=3)
assert False,cgel_tree.draw() #(cgel_tree.tokens[3].constituent,cgel_tree.tokens[3].deprel)
"""
