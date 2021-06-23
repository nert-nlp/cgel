import re, glob


def parse(filename, fout):
    with open(filename, 'r') as fin:
        text = fin.read().replace('\n', ';')
        filename = re.search(r'/(.*?)\.tex', filename).group(1)
        for num, tree in enumerate(re.findall(r'\\begin\{parsetree\}.*?\\end\{parsetree\}', text)):
            fout.write(f'Tree {filename}-{num}\n')

            stack = []
            label_id = 0
            left, right = 0, 0
            deps = []
            for i, char in enumerate(tree):
                if char == '(':
                    label = re.search(r'^\(.*?\.(.*?)\.', tree[i:]).group(1)
                    if 'SIEG' in filename:
                        sublabels = re.search(r'\\begin\{tabular\}\{c\}(.*?)\\end\{tabular\}', label)
                    else:
                        sublabels = re.search(r'\\NL\{(.*?)\}\{(.*?)\}', label)
                    word = "_"
                    if sublabels:
                        if 'SIEG' in filename:
                            label = sublabels.group(1).split('\\\\')
                            label[0] = label[0].strip(':')
                            if len(label) == 1:
                                label.append('')
                        else:
                            label = [sublabels.group(1), sublabels.group(2)]
                            label[1] = label[1].replace('\\textsubscript{', '_')
                        words = re.search(r'^[^\)\(]*?`(.*?)\' *?\)', tree[i + 1:])
                        if words:
                            word = words.group(1)
                            left = right
                            right = right + len(word.split()) - 1
                    else:
                        label = [label, '']

                    parent = -1 if len(stack) == 0 else stack[-1]
                    deps.append([left, right, word, label, parent])
                    stack.append(label_id)
                    label_id += 1
                    if word != '_':
                        left = right + 1
                        right = left
                if char == ')':
                    stack.pop()
            
            for i in range(len(deps) - 1, -1, -1):
                parent = deps[i][4]
                if parent != -1:
                    deps[parent][0] = min(deps[i][0], deps[parent][0])
                    deps[parent][1] = max(deps[i][1], deps[parent][1])
            
            cts = {}
            labels = []

            words = []
            consts = []
            for i in deps:
                i[0] += 1
                i[1] += 1
                label = str(i[0]) if i[0] == i[1] else f'{i[0]}-{i[1]}'
                labels.append(label)

                if label not in cts: cts[label] = 0
                cts[label] += 1

                if i[2] != '_':
                    words.append(f'{label + "’" * (cts[label] - 1)}\t{i[2]}\n')
                    cts[label] += 1
                consts.append(f'{label + "’" * (cts[label] - 1)}\t{i[3][0]}\t{i[3][1]}\t{"0" if i[4] == -1 else labels[i[4]]}\n')

            fout.write(' '.join([i[2] for i in deps if i[2] != '_']) + '\n')
            fout.write(''.join(words))
            fout.write(''.join(consts))
            fout.write('\n')
            

with open('parsed.txt', 'w') as fout:
    for file in glob.glob('trees/*.tex'):
        print(file)
        parse(file, fout)