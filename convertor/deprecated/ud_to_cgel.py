import csv
from tqdm import tqdm
from rows import *
import pickle

def rules(rows):
    apply_rule(Row(deprel="nummod"), Row(deprel="det"), rows, "nummod to det")
    apply_rule(Row(deprel="det"), Row(deprel="Det"), rows, "det to Det")
    apply_rule(Row(deprel="amod"), Row(deprel="Mod"), rows, "amod to Mod")
    return rows

def preliminary():
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
    rows = []

    with open('en_ewt-ud-train.conllu', 'r') as fin, open('en_ewt-cgel.txt', 'w') as fout:
        reader = csv.reader(fin, delimiter='\t', quoting=csv.QUOTE_NONE)
        row_buffer = []
        buffer = []
        for row in reader:
            if not row:
                pass
            elif row[0].startswith('#'):
                for rule in special:
                    length = len(rule[0])
                    for i in range(len(buffer)):
                        if length <= i + 1 and buffer[i + 1 - length:i + 1] == rule[0]:
                            if len(rule[1]) == 1:
                                new = ' '.join([x[0] for x in rule[0]])
                                for j in range(length-1):
                                    buffer[i + 1 - length + 1 + j] = ('', '')
                                buffer[i + 1 - length] = (new, rule[1][0])
                            else:
                                for j in range(length):
                                    buffer[i + 1 - length + j] = (rule[0][j][0], rule[1][j])
                for i, word in enumerate(buffer):
                    rows.append(
                        Row(
                            word=word[0],
                            lemma=row_buffer[i][2],
                            pos=word[1],
                            head=row_buffer[i][6],
                            deprel=row_buffer[i][7],
                            misc=row_buffer[i][9]
                        )
                    )
                    # fout.write(f'{word[0]}\t{general.get(word[1], word[1])}\n')
                # if buffer:
                #     fout.write('\n')
                buffer = []
                row_buffer = []
                rows.append(Row(word='\t'.join(row) + '\n'))
                # fout.write('\t'.join(row) + '\n')
            else:
                buffer.append((row[1], row[3]))
                row_buffer.append(row)
            pbar.update(1)
    pbar.close()

    return rows

def main():
    # rows = preliminary()
    # with open('rows.txt', 'wb') as fout:
    #     pickle.dump(rows, fout)
    with open('rows.txt', 'rb') as fin:
        rows = pickle.load(fin)
    rows = rules(rows)
    with open('en_ewt-cgel.txt', 'w') as fout:
        for row in rows:
            if row.word.startswith('#'):
                fout.write(f"\n{row.word}\n")
            else:
                fout.write(f"{row.word}\t{row.lemma}\t{row.pos}\t{row.head}\t{row.deprel}\t{row.misc}\n")

if __name__ == "__main__":
    main()