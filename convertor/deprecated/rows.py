
import re

class Row:
    def __init__(self, word=r".*", lemma=r".*", pos=r".*", head=r".*", deprel=r".*", misc=r".*"):
        self.word = word
        self.lemma = lemma
        self.pos = pos
        self.head = head
        self.deprel = deprel
        self.misc = misc

def match(comp, check):
    if check.word.startswith('#'):
        return False
    res = True
    res = res and (re.search(comp.word, check.word))
    res = res and (re.search(comp.lemma, check.lemma))
    res = res and (re.search(comp.pos, check.pos))
    res = res and (re.search(comp.head, check.head))
    res = res and (re.search(comp.deprel, check.deprel))
    res = res and (re.search(comp.misc, check.misc))
    return res

def apply_rule(comp, new, rows, label):
    ct = 0
    for row in rows:
        if match(comp, row):
            if new.word != r".*": row.word = new.word
            if new.lemma != r".*": row.lemma = new.lemma
            if new.pos != r".*": row.pos = new.pos
            if new.head != r".*": row.head = new.head
            if new.deprel != r".*": row.deprel = new.deprel
            if new.misc != r".*": row.misc = new.misc
            ct += 1
    print(f"{label}: {ct} replacement(s)")