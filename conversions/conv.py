import csv
from tqdm import tqdm

general = {}
with open('general.csv', 'r') as fin:
    reader = csv.reader(fin)
    for i, row in enumerate(reader):
        if i == 0: continue
        if row[1] == '':
            row[1] = '?'
        general[row[1]] = row[0]

special = []
with open('words.csv', 'r') as fin:
    reader = csv.reader(fin)
    for i, row in enumerate(reader):
        if i == 0: continue
        words = row[0].split()
        pos = row[3].split(' + ')
        res = row[1].split(' + ')
        match = list(zip(words, pos))
        special.append((match, res))

special.sort(key=lambda x: -len(x[0]))
# print([x[0] for x in special])

pbar = tqdm(total=247861)

with open('en_ewt-ud-train.conllu', 'r') as fin, open('en_ewt-cgel.txt', 'w') as fout:
    reader = csv.reader(fin, delimiter='\t', quoting=csv.QUOTE_NONE)
    buffer = []
    for row in reader:
        if not row:
            pass
        elif row[0].startswith('#'):
            for rule in special:
                length = len(rule[0])
                for i in range(len(buffer)):
                    if length <= i + 1 and buffer[i + 1 - length:i + 1] == rule[0]:
                        # print('yeet')
                        # print(rule)
                        # print(buffer)
                        if len(rule[1]) == 1:
                            new = ' '.join([x[0] for x in rule[0]])
                            for j in range(length-1):
                                buffer[i + 1 - length + 1 + j] = ('', '')
                            buffer[i + 1 - length] = (new, rule[1][0])
                        else:
                            for j in range(length):
                                buffer[i + 1 - length + j] = (rule[0][j][0], rule[1][j])
                        # print(buffer)
                        # input()
            for word in buffer:
                fout.write(f'{word[0]}\t{general.get(word[1], word[1])}\n')
            if buffer:
                fout.write('\n')
            buffer = []
            fout.write('\t'.join(row) + '\n')
        else:
            buffer.append((row[1], row[3]))
        pbar.update(1)
pbar.close()
