import glob
from cgel import Tree
import re
from tqdm import tqdm
import conllu
import ud_to_cgel

node = re.compile(r'\\(.*?)\{(.*)\}')
textsf = re.compile(r'\\textsf\{(.*?)\}\\\\(.+)')
textit = re.compile(r'\\textit\{(.*?)\}')

function_map = {
    'Mk': 'Marker',
    'Sup': 'Supplement',
    'Crd': 'Coordinate'
}

def parse_constituent(constituent, ct):
    constituent = constituent.split(',')[0]
    constituent = re.sub(r'\\textdollar *', r'$', constituent)

    if 'textit' in constituent:
        constituent = textit.search(constituent).group(1)

    res = node.search(constituent)
    if 'textsf' in constituent:
        res = textsf.search(constituent)

    ret = []
    if ct == 0:
        ret = [None, None, constituent]
    elif res:
        if '}{' in res.group(2):
            ret = [None] + list(res.group(2).split('}{'))
        else:
            ret = [None, res.group(1), res.group(2)]
    else:
        ret = [constituent, None, None]
    if ret[2]:
        ret[2] = re.sub(r'\\textsubscript({\\textsc)?{(.*?)(})?}', r'_\2', ret[2])
    if ret[1]:
        ret[1] = re.sub(r'\\textsubscript({\\textsc)?{(.*?)(})?}', r'_\2', ret[1])

    return tuple(ret)

def get_ud():
    sentences = []
    with open('datasets/cgel_from_ud/training_set_all.txt') as fin:
        for line in fin:
            sentences.append(line.strip().replace('# text = ', ''))
    ud = {}
    print('Getting UD')
    with open('datasets/cgel_from_ud/ud_train.conllu') as fin:
        for token_list in tqdm(conllu.parse_incr(fin)):
            if token_list.metadata['text'] in sentences:
                ud[token_list.metadata['text']] = token_list
    with open('datasets/cgel_from_ud/ud_train.conllu', 'w') as fout:
        for sent in sentences:
            if sent in ud:
                fout.write(ud[sent].serialize())
    ud_to_cgel.convert('datasets/cgel_from_ud/ud_train.conllu', 'datasets/cgel_from_ud/result.txt', 'datasets/cgel_from_ud/cgel.trees')
    

def parse():
    trees = []
    for file in tqdm(sorted(glob.glob('trees/TrainingSet1 2/*.tex'))):
        # print(file)
        ct = 0
        tree = Tree()

        with open(file, 'r') as fin:
            parsing, active = False, False
            cur = ""
            stack = [('', -1)]
            for line in fin:
                # print(line)
                if line.startswith('%'): continue
                if '\\begin{forest}' in line and not parsing:
                    parsing = True
                elif parsing:
                    if '\\end{forest}' in line:
                        parsing = False
                    else:
                        for char in line:
                            if char == '%': break
                            if char == '[':
                                if cur != "":
                                    cur = cur.strip()
                                    p = parse_constituent(cur, ct)
                                    tree.add_token(p[0], p[1], p[2], ct, stack[-1][1])
                                    stack.append((cur, ct))
                                    ct += 1
                                # print('push', stack)
                                cur = ""
                                active = True
                            elif char == ']':
                                if cur != "":
                                    cur = cur.strip()
                                    p = parse_constituent(cur, ct)
                                    tree.add_token(p[0], p[1], p[2], ct, stack[-1][1])
                                    stack.append((cur, ct))
                                    ct += 1
                                    cur = ""
                                stack.pop()
                                if len(stack) == 1:
                                    trees.append((file, tree))
                                    tree = Tree()
                                    ct = 0
                                # print('pop', stack)
                                active = False
                            elif active:
                                cur += char


    with open('datasets/cgel_from_ud/training_set.txt', 'w') as fout:
        for file, tree in trees:
            tree.prune('phantom')
            tree.prune('hspace')
            fout.write(file + '\n')
            fout.write(tree.sentence() + '\n')
            fout.write(str(tree) + '\n\n')

def main():
    # parse()
    get_ud()

if __name__ == '__main__':
    main()