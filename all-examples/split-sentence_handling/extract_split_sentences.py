import re

RE_SPLIT = re.compile(r'(>| )/(\*| |<)')

if __name__ == '__main__':
    pagified = open('../pagified.html', 'r', encoding="utf-8").readlines()
    splits = []
    for line in pagified:
        if re.search(RE_SPLIT, line) is not None:
            splits.append(line)

    splits_doc = '\n'.join(splits)

    print(splits_doc)
