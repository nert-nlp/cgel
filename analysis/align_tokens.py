import conllu
import sys
sys.path.append('../')
import cgel
from cgel import Node
from collections import Counter
from math import log
from difflib import get_close_matches

"""
This was written to align original versions of the .cgel trees with the UD tokenization,
add subtype V -> V_aux, and import UD lemmas/punctuation/subtokens.
Note that once the .cgel trees are so enhanced, validate_ud_alignment.py should be
used to check that the trees correspond.
"""

ADD_PUNCT_AND_SUBTOKS = True
INFER_VAUX = False
INFER_LEMMA = True
ADD_XPOS = {'CD', 'MD', 'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ'}  # add XPOS tags in this list

with open('../datasets/twitter.conllu') as f, open('../datasets/trial/twitter-etc-trial.conllu') as f2:
    ud_trees = conllu.parse( #f.read() +
        f2.read())

cgel_trees = []
with open('../datasets/twitter.cgel') as f, open('../datasets/trial/twitter-etc-trial.cgel') as f2:
    for tree in cgel.trees(f2):
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
    if cgel_tree.sentid.startswith('???'):  # temporary ID; copy the UD one
        cgel_tree.sentid = ud_tree.metadata['sent_id']
    if cgel_tree.text=='???':   # temporary text string; copy the UD one
        cgel_tree.text = ud_tree.metadata['text']
    cgel_sentid = cgel_tree.sentid
    cgel_sent = cgel_tree.sent
    cgel_toks = [node for node in cgel_tree.tokens.values() if node.text or node.constituent=='GAP']
    udnI = ud_tok_scanner(ud_tree)
    udn = None
    last_nongap = None
    hold_word = None
    unhold = False
    for n in cgel_toks:
        if n.constituent=='GAP':
            sentid = cgel_sentid
            gapij = f'{udn["id"] if udn else 0}/{udn["id"]+1 if udn else 1}'
            gaps.add((sentid, gapij))
            continue
        last_nongap = n
        buf = n.text
        #buf = buf.replace("''", '"') # "clitic" sentence
        if not hold_word or not buf.lower().startswith(hold_word['form'].lower()):
            udn = next(udnI,None)
            #if hold_word is not None: print('next116', file=sys.stderr)
        if udn is None:
            assert False,('UD: EOS',cgel_sentid)
        # if hold_word is not None:
        #     print(buf, udn['form'], file=sys.stderr)
        while not buf.lower().startswith(udn['form'].lower()) and (buf,udn['form']) not in EWT_MISTRANSCRIPTIONS | EWT_SPELLING_CORRECTIONS_IN_CGEL:
            if udn['deprel']=='punct':
                insert_prepunct(n, udn['form'])
                #print('UD punct:', udn['form'])
            elif hold_word:
                # process currency symbol that we saved from before
                udn = hold_word
                #print('unhold', file=sys.stderr)
                hold_word = None
                continue
            elif udn['xpos']=='$':  # currency symbol e.g. "$" moved after amount in CGEL
                hold_word = udn
                #print('holding',buf,udn['form'], file=sys.stderr)
            else:
                assert False,f'UD-only word: {udn["form"]:10} #' + cgel_sentid.rsplit('/')[-1].split('.')[0] + ' ' + cgel_tree.sentence()

            udn = next(udnI, None)
            # if hold_word is not None:
            #     print('next138', file=sys.stderr)
            #     print(buf,'//',udn['form'], file=sys.stderr)
            if udn is None:
                assert False,('UD: EOS',cgel_sentid)
                break
        #if hold_word is not None: print(buf,'=',udn['form'], file=sys.stderr)
        if n.correct:   # ignore :correct ""
            if n.correct!=(udn.get('misc') or {}).get('CorrectForm'):
                print(':correct without CorrectForm? (OK if in another part of multiword token)', n.correct,(udn.get('misc') or {}).get('CorrectForm'),udn['form'], file=sys.stderr)

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

            # special rules for possessive/reflexive pronoun lemmas, copied from validate_ud_alignment.py
            if udn['upos']=='PRON' and (udn['feats'] or {}).get('Poss')=='Yes': # note that PRP$/WP$ doesn't include 'mine' etc.
                cgellemma = {'my': 'I', 'mine': 'I', 'your': 'you', 'yours': 'you',
                            'his': 'he', 'her': 'she', 'hers': 'she', 'its': 'it',
                            'our': 'we', 'ours': 'we', 'their': 'they', 'theirs': 'they'}[udn['lemma']]
            elif udn['upos']=='PRON' and (udn['feats'] or {}).get('Reflex')=='Yes':
                cgellemma = {'myself': 'I', 'ourselves': 'we',
                            'yourself': 'you', 'yourselves': 'you',
                            'himself': 'him', 'herself': 'her', 'itself': 'it',
                            'themselves': 'they'}[udn['lemma']]
            else:
                cgellemma = udn['lemma']

            if cgellemma!=buf:
                if cgellemma.lower()==t.lower():
                    print(cgellemma,t, file=sys.stderr)
                n.lemma = cgellemma
            # if not explicitly set, the lemma defaults to the token form

        if udn['xpos'] in ADD_XPOS:
            if n.lemma==udn['lemma']:
                if udn['xpos']=='CD':
                    if n.constituent in ('D', 'N'):
                        n.xpos = udn['xpos']
                    else:
                        print('Expected D or N:', n.lexeme, n.constituent, udn['xpos'], file=sys.stderr)
                else:
                    if n.constituent in ('V', 'V_aux'):
                        n.xpos = udn['xpos']
                    else:
                        print('Expected V(_aux):', n.lexeme, n.constituent, udn['xpos'], file=sys.stderr)
            else:
                print('Unexpected lemma:', n.lexeme, n.lemma, n.constituent, udn['lemma'], udn['xpos'], file=sys.stderr)
        elif n.constituent in ('V', 'V_aux'):
            print('Missing xpos:', n.lexeme, file=sys.stderr)

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
                if udn['upos']=='PUNCT':
                    insert_subpunct(n, udn['form'])
                else:
                    insert_subtoken(n, udn['form'])
                buf = buf[len(udn['form']):]
            if buf and buf[0]==' ':
                buf = buf[1:]
            if buf:
                # We've matched part of buf but there is more (multiple corresponding UD nodes). grab the next one
                udn = next(udnI)
                if hold_word is not None: print('next188', file=sys.stderr)

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
    for fld,val in cgel_tree.metadata.items():
        if fld not in ('sent_id','sent_num','alias','text','sent'):
            print(f'# {fld} = {val}')
    print(cgel_tree.draw())
    print()


print(gaps, file=sys.stderr)
"""
cgel_tree.tokens[70] = cgel.Node(deprel="Extra",constituent="X",head=3,text="extraextra")
cgel_tree.children[3].append(70)
#cgel_tree.add_token(token="extraextra",deprel="Extra",constituent="X",i=70,head=3)
assert False,cgel_tree.draw() #(cgel_tree.tokens[3].constituent,cgel_tree.tokens[3].deprel)
"""
