from depedit import DepEdit
import conllu
from collections import defaultdict
import constituent
import copy
from tqdm import tqdm

test = False

filename = "en_ewt-ud-train.conllu.txt"
if test:
    filename = "practice.conllu.txt"

print('Getting files...')
infile = open(filename)
config_file  = open("../convertor/ud-to-cgel.ini")
d = DepEdit(config_file)

print('Running depedit...')
result = d.run_depedit(infile)

print('Done with depedit.')
types = defaultdict(int)
pos = defaultdict(int)

sent = [0, 0, 0]
tok = [0, 0]

def penman(node, d, add_head):
    # print(u, children[u])
    add = False
    res = ''
    upos, form, deprel = node.token['upos'], node.token['form'], node.token['deprel']

    if deprel == 'Clause':
        res = f'({deprel}'
    else:
        if ':' in deprel:
            rel, pos = deprel.split(':')
        else:
            rel, pos = deprel, upos
        res += f'\n{"    " * d}:{rel} ({pos}'
    if not add_head and form != '_':
        res += f' :t "{form}"'
    
    for child in node.children:
        if child.token["id"] > node.token["id"] and not add and add_head:
            res += f'\n{"    " * (d + 1)}:Head ({upos} :t "{form}")'
            add = True
        res += penman(child, d + 1, add_head)
    if not add and add_head:
        res += f'\n{"    " * (d + 1)}:Head ({upos} :t "{form}")'

    res += ')'
    return res

# create projected constituents recursively
def project_categories(node):
    if test:
        print(node.token['form'])
    upos, form, deprel = node.token['upos'], node.token['form'], node.token['deprel']

    if deprel == 'Clause':
        rel, pos = 'Root', 'Clause'
    elif ':' in deprel:
        rel, pos = deprel.split(':')
    else:
        rel, pos = deprel, upos

    # collect all the new projected categories for reference
    projected = {}

    # keep track of child to control
    last = node
    status = True
    if upos in constituent.projections:

        # go through all projected categories
        for level in constituent.projections[upos]:

            # make new node
            if test:
                print(f'    Projecting new node: {level}')
            head = copy.deepcopy(node)
            head.token['form'] = '_'
            head.token['upos'] = level
            head.token['deprel'] = f'{rel}:{level}'
            head.children = [last]
            projected[level] = head
            if test:
                print('   ', head.token)

            # deprel of child node must be Head
            last.token['deprel'] = last.token['deprel'].replace(f'{rel}:', 'Head:')
            last = head

            # if we reach last projected category, break
            # its pos is simply what we stored in upos!
            if level == pos:
                node.token['deprel'] = node.token['deprel'].replace(f':{pos}', f':{upos}')
                break
    
        remaining = []
        for i, child in enumerate(node.children):
            rel = child.token['deprel'].split(':')[0]
            level = constituent.level.get((rel, upos), None)
            result, status2 = project_categories(child)
            status = status and status2
            if level and level in projected:
                # print(f'Moving to {level}')
                projected[level].children.append(result)
                projected[level].children.sort(key=lambda x: x.token['id'])
            else:
                remaining.append(result)
            
        last.children.extend(remaining)
        last.children.sort(key=lambda x: x.token['id'])
        node.children = []
    else:
        status = False
        for i, child in enumerate(node.children):
            node.children[i], _ = project_categories(child)

    return last, status

print('Converting to constituency...')
with open('cgel.trees.txt', 'w') as fout:
    for sentence in tqdm(conllu.parse(result)):
        try:
            sent[1] += 1
            parsed = True
            children = [[] for i in range(len(sentence) + 1)]

            for word in sentence:
                tok[1] += 1
                if word['deprel'].islower():
                    parsed = False
                else:
                    tok[0] += 1
                pos[word['upos']] += 1
                types[(word['upos'], word['deprel'])] += 1

            for key in sentence.metadata:
                fout.write(f'{key} = {sentence.metadata[key]}\n')

            tree = sentence.to_tree()

            fixed, status = project_categories(sentence.to_tree())
            if status:
                sent[2] += 1
            if test:
                print(status)
                print(penman(tree, 0, True))
                print(penman(fixed, 0, False))
            fout.write(penman(fixed, 0, False))
            fout.write('\n\n')

            if parsed:
                sent[0] += 1
        except Exception as e:
            print(e)
            print(sentence)

with open('results.txt', 'w') as fout:
    fout.write(f'{sent[0]} / {sent[1]} sentences fully parsed ({sent[0] / sent[1]}).\n')
    fout.write(f'{sent[2]} / {sent[1]} sentences with all projections known ({sent[2] / sent[1]}).\n')
    fout.write(f'{tok[0]} / {tok[1]} words fully parsed ({tok[0] / tok[1]}).\n')
    fout.write('POS\n')
    for i in pos:
        fout.write(f'{i}, {pos[i]}\n')
    fout.write('\n')
    fout.write('DEP\n')
    for i in types:
        fout.write(f'{i}, {types[i]}\n')

with open('cgel.conllu', 'w') as fout:
    fout.write(result)