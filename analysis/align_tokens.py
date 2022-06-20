import conllu
import sys
sys.path.append('../')
import cgel
from cgel import Node
from collections import Counter
from math import log
from difflib import get_close_matches

with open('../datasets/twitter_ud.conllu') as f, open('../datasets/ewt_ud.conllu') as f2:
    ud_trees = conllu.parse(f.read() + f2.read())

cgel_trees = []
with open('../datasets/twitter_cgel.txt') as f, open('../datasets/ewt_cgel.txt') as f2:
    a = ''.join([x for x in f.readlines() + f2.readlines() if x[0] in [' ', '(']])
    for tree in cgel.parse(a):
        cgel_trees.append(tree)
        #trees.append(conllu.parse(tree.to_conllu())[0])

def ud_tok_scanner(ud_tree):
    for node in ud_tree:
        if isinstance(node['id'], int): # skip token ranges
            yield node

def insert_subtoken(cgel_node: Node, subtoken: str):    # lexical material that is tokenized more aggressively in UD than CGEL
    cgel_node.substrings = (cgel_node.substrings or []) + [(':subt', subtoken)]

def insert_subpunct(cgel_node: Node, punct: str):    # UD-segmented punctuation within a lexical item (e.g. hyphen)
    cgel_node.substrings = (cgel_node.substrings or []) + [(':subp', punct)]

def insert_prepunct(cgel_node: Node, punct: str):
    cgel_node.prepunct += (punct,)

def insert_postpunct(cgel_node: Node, punct: str):
    cgel_node.postpunct += (punct,)

# (CGEL,EWT)
EWT_MISTRANSCRIPTIONS = {("200","200,000"),("San","Sao"),("Grill","Grille"),("investigators","interrogators"),
    ("favour","favor"),("issues","issue"),("trouble","problems"),("sushi","sashimi"),("sashimi","sushi"),
    ("lawyers","politicians"),("politicians","lawyers")}
EWT_SPELLING_CORRECTIONS_IN_CGEL = {("lose","Loose"),("billings","Billing"),("schedule","scheduled")}

assert len(ud_trees)==len(cgel_trees)
for ud_tree,cgel_tree in zip(ud_trees,cgel_trees):
    cgel_toks = [node for node in cgel_tree.tokens.values() if node.text]
    udnI = ud_tok_scanner(ud_tree)
    for n in cgel_toks:
        buf = n.text
        buf = buf.replace('_x','').replace('_y','').replace('_x/y','').replace('/y','') # beyonce sentence
        buf = buf.replace("''", '"') # "clitic" sentence
        udn = next(udnI,None)
        if udn is None:
            print('UD: EOS')
        while not buf.lower().startswith(udn['form'].lower()) and (buf,udn['form']) not in EWT_MISTRANSCRIPTIONS | EWT_SPELLING_CORRECTIONS_IN_CGEL:
            if udn['deprel']=='punct':
                insert_prepunct(n, udn['form'])
                print('UD punct:', udn['form'])
            else:
                print(f'UD ???: {udn["form"]:10} ' + cgel_tree.sentence())
            if udn['form']=="I'm":
                assert False,(udn,)
            udn = next(udnI, None)
            if udn is None:
                print('UD: EOS')
                break
        print(buf)
        if buf=='yet' and not udn:
            print('Skipping missing word: yet')
            continue
        assert udn
        if len(buf)==len(udn['form']) or (buf,udn['form']) in {("if'","If"), ("of'","of")} | EWT_MISTRANSCRIPTIONS | EWT_SPELLING_CORRECTIONS_IN_CGEL:
            continue
        while buf:
            if not buf.lower().startswith(udn['form'].lower()) and (buf,udn['form']) not in {("n't", 'n’t')}:
                if buf.startswith('-') and not udn['form'].startswith('-'):
                    print('CGEL-only subpart: -')
                    buf = buf[1:]
                    continue
                assert udn['form']=='-',(buf,udn['form'])
                print('UD infix:', udn['form'])
                insert_subpunct(n, udn['form'])
            else:
                print('UD subtok:', udn['form'])
                insert_subtoken(n, udn['form'])
                buf = buf[len(udn['form']):]
            if buf and buf[0]==' ':
                buf = buf[1:]
            if buf:
                udn = next(udnI)
    print()
    print(cgel_tree.draw())
    print()

"""
cgel_tree.tokens[70] = cgel.Node(deprel="Extra",constituent="X",head=3,text="extraextra")
cgel_tree.children[3].append(70)
#cgel_tree.add_token(token="extraextra",deprel="Extra",constituent="X",i=70,head=3)
assert False,cgel_tree.draw() #(cgel_tree.tokens[3].constituent,cgel_tree.tokens[3].deprel)
"""
