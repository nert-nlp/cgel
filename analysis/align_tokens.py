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

with open('../datasets/twitter_ud.conllu') as f, open('../datasets/ewt_ud.conllu') as f2:
    ud_trees = conllu.parse( #f.read() +
        f2.read())

cgel_trees = []
cgel_headers = []
with open('../datasets/twitter_cgel.txt') as f, open('../datasets/ewt_cgel.txt') as f2:
    tree_lines = []
    for x in (#f.readlines() +
        f2.readlines()):
        if x[0] in (' ', '('):
            assert '\t' not in x,"Tree line shouldn't contain tab character"
            tree_lines.append(x)
        elif x[0].isspace() and x.strip():
            # Non-empty line starting with invalid space
            assert False,f"Invalid start of line: {x!r}"
        elif not x[0].isspace():
            cgel_headers.append(x.strip())
    cgel_sentids, cgel_sents = cgel_headers[::2], cgel_headers[1::2]
    for tree in cgel.parse(''.join(tree_lines)):
        cgel_trees.append(tree)
        #trees.append(conllu.parse(tree.to_conllu())[0])
    assert len(cgel_sentids)==len(cgel_sents)==len(cgel_trees)

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
     70 get ** NOT A CGEL Vaux: The city got destroyed -> did not get destoryed/*got not destroyed; Did the city get destroyed?/*Got the city destroyed?
   1984 have
    244 may
    109 might
    101 must
      2 ought
     35 shall
    345 should
   1472 will
   1006 would

Retag as Vaux?  is | not that there is anything wrong with that because they also employ local people that that live and shop in the area
Retag as Vaux?  is | you should give her a try it 's worth every penny to know that you pet is in great hands with Wunderbar pet sitting
Retag as Vaux? are | but there are strong hints in the country that a new Indo - Sri Lanka defense deal could be in the making
Retag as Vaux?  is | this person is not coming to visit you the whole point of this scam is to gain your trust enough to steal your money and identity
Retag as Vaux?  is | what we are trying to do is solicit votes for the band in order to put them in first place
Retag as Vaux?  's | he doesn't just take pictures he makes art out of them and you won't even notice that there 's a camera there
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
for ud_tree,cgel_tree,cgel_sentid,cgel_sent in zip(ud_trees,cgel_trees,cgel_sentids,cgel_sents):
    cgel_toks = [node for node in cgel_tree.tokens.values() if node.text or node.constituent=='GAP']
    udnI = ud_tok_scanner(ud_tree)
    for n in cgel_toks:
        if n.constituent=='GAP':
            sentid = ud_tree.metadata['sent_id']
            gapij = f'{udn["id"]}/{udn["id"]+1}'
            gaps.add((sentid, gapij))
            continue
        buf = n.text
        buf = buf.replace('_x','').replace('_y','').replace('_x/y','').replace('/y','') # beyonce sentence
        buf = buf.replace("''", '"') # "clitic" sentence
        udn = next(udnI,None)
        if udn is None:
            assert False,'UD: EOS'
        while not buf.lower().startswith(udn['form'].lower()) and (buf,udn['form']) not in EWT_MISTRANSCRIPTIONS | EWT_SPELLING_CORRECTIONS_IN_CGEL:
            if udn['deprel']=='punct':
                insert_prepunct(n, udn['form'])
                #print('UD punct:', udn['form'])
            else:
                assert False,f'UD-only word: {udn["form"]:10} #' + cgel_sentid.rsplit('/')[-1].split('.')[0] + ' ' + cgel_tree.sentence()

            udn = next(udnI, None)
            if udn is None:
                assert False,'UD: EOS'
                break
        assert n.correct==(udn.get('misc') or {}).get('CorrectForm'),(n.correct,(udn.get('misc') or {}).get('CorrectForm'))

        if INFER_VAUX:
            if udn['upos']=='AUX':
                if udn['lemma']!='get':    # get is not a CGEL Vaux
                    assert udn['lemma'] in AUX_LEMMAS,n.text
                    assert n.constituent=='V',n
                    n.constituent = 'Vaux'
            elif udn['upos']=='VERB' and udn['lemma'] in AUX_LEMMAS:
                print('Retag as Vaux?', n.text, cgel_tree.sentence(), file=sys.stderr)

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
                assert udn['form']=='-',(buf,udn['form'])
                #print('UD infix:', udn['form'])
                insert_subpunct(n, udn['form'])
            else:
                #print('UD subtok:', udn['form'])
                insert_subtoken(n, udn['form'])
                buf = buf[len(udn['form']):]
            if buf and buf[0]==' ':
                buf = buf[1:]
            if buf:
                udn = next(udnI)

    # Print the metadata and tree (with any modifications)
    s = cgel_tree.sentence(gaps=True)
    if s!=cgel_sent:
        print('MISMATCH:', s,'||',cgel_sent, file=sys.stderr)
    print(cgel_sentid)
    print(cgel_sent)
    print(cgel_tree.draw())
    print()


#print(gaps, file=sys.stderr)
"""
cgel_tree.tokens[70] = cgel.Node(deprel="Extra",constituent="X",head=3,text="extraextra")
cgel_tree.children[3].append(70)
#cgel_tree.add_token(token="extraextra",deprel="Extra",constituent="X",i=70,head=3)
assert False,cgel_tree.draw() #(cgel_tree.tokens[3].constituent,cgel_tree.tokens[3].deprel)
"""
