import re

RE_SPLIT = re.compile(r'(<(u|small-caps)>[A-Za-z _\.]+ ?</(u|small-caps)>)( ?</(em|small-caps|u)>(<sub>i</sub>)? ?/ ?\*?<(em|small-caps|u)> ?)(<(u|small-caps)> ?[A-Za-z _\.]+</(u|small-caps)>(<sub>i</sub>)?)')

if __name__ == '__main__':
    splits = open('split_sentences_unsplit.html', 'r', encoding="utf-8").readlines()
    all = []
    for line in splits:
        all.append(line)
        if re.search(RE_SPLIT, line) is not None:
            print(line)
            split1 = re.sub(RE_SPLIT, r'\1', line)
            print(split1)
            split2 = re.sub(RE_SPLIT, r'\8', line)
            print(split2)
            all.append(split1)
            all.append(split2)

    splits_doc = ''.join(all)

    print(splits_doc)
