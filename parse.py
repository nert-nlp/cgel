import re, glob

def parse(filename, fout):
    with open(filename, 'r') as fin:
        text = fin.read().replace('\n', ';')
        filename = re.search(r'/(.*?)\.tex', filename).group(1)
        for num, tree in enumerate(re.findall(r'\\begin\{parsetree\}.*?\\end\{parsetree\}', text)):
            fout.write(f'Tree {filename}-{num}\n')

            stack = []
            label_id = 1
            for i, char in enumerate(tree):
                if char == '(':
                    label = re.search(r'^\(.*?\.(.*?)\.', tree[i:]).group(1)
                    if 'SIEG' in filename:
                        sublabels = re.search(r'\\begin\{tabular\}\{c\}(.*?)\\end\{tabular\}', label)
                    else:
                        sublabels = re.search(r'\\NL\{(.*?)\}\{(.*?)\}', label)
                    word = None
                    if sublabels:
                        if 'SIEG' in filename:
                            label = sublabels.group(1).split('\\\\')
                        else:
                            label = [sublabels.group(1), sublabels.group(2)]
                        words = re.search(r'^[^\)\(]*?`(.*?)\' *?\)', tree[i + 1:])
                        if words:
                            word = words.group(1)
                    else:
                        label = [label]
                    fout.write(f'{label_id}\t{word if word else "-"}\t{",".join(label)}\t{0 if len(stack) == 0 else stack[-1]}\n')
                    stack.append(label_id)
                    label_id += 1
                if char == ')':
                    stack.pop()
            
            fout.write('\n')

with open('parsed.txt', 'w') as fout:
    for file in glob.glob('trees/*.tex'):
        print(file)
        parse(file, fout)