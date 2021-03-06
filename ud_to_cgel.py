from depedit import DepEdit
import conllu
from collections import defaultdict
import constituent
import copy
from tqdm import tqdm
import random

test = False

def convert(infile, resfile, outfile):
    print('Getting files...')
    infile = open(infile)
    config_file  = open("convertor/ud-to-cgel.ini")
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
        depth = 1
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
            res_c, depth_c = penman(child, d + 1, add_head)
            res += res_c
            depth = max(depth, depth_c + 1)
        if not add and add_head:
            res += f'\n{"    " * (d + 1)}:Head ({upos} :t "{form}")'

        res += ')'
        return res, depth

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
            if upos != pos:
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

    logs = []

    print('Converting to constituency...')
    with open(outfile + '.txt', 'w') as fout:
        trees = conllu.parse(result)
        # random.shuffle(trees)
        ct = 0
        for sentence in tqdm(trees):
            print(sentence.metadata['text'])
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

            tree = sentence.to_tree()

            fixed, status = project_categories(sentence.to_tree())
            if status:
                sent[2] += 1
            if test:
                print(status)
                print(penman(tree, 0, True)[0])
                print(penman(fixed, 0, False)[0])
            output, depth = penman(fixed, 0, False)

            # if ct >= 200:
            #     break
            # if len(sentence) < 15 or len(sentence) > 30:
            #     continue
            ct += 1

            # for key in sentence.metadata:
            #     fout.write(f'{key} = {sentence.metadata[key]}\n')
            fout.write(sentence.serialize())
            fout.write(output)
            logs.append([depth, len(sentence), parsed])
            fout.write('\n\n')

            if parsed:
                sent[0] += 1

    # print(ct)
    # depth_good, length_good = defaultdict(int), defaultdict(int)
    # depth_tot, length_tot = defaultdict(int), defaultdict(int)
    # for depth, length, status in logs:
    #     if status:
    #         depth_good[depth] += 1
    #         length_good[length] += 1
    #     depth_tot[depth] += 1
    #     length_tot[length] += 1
    # for i in range(40):
    #     print(i, depth_good[i], depth_tot[i], (depth_good[i] / (depth_tot[i] or 1)))
    # for i in range(100):
    #     print(i, length_good[i], length_tot[i], (depth_good[i] / (length_tot[i] or 1)))

    with open(resfile, 'w') as fout:
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

    with open(outfile + '.conllu', 'w') as fout:
        fout.write(result)

def main():
    convert('conversions/en_ewt-ud-train.conllu.txt', 'conversions/results.txt', 'conversions/cgel.trees')

if __name__ == '__main__':
    main()