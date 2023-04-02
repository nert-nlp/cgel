"""
Given a set of sentids, extract the relevant .conllu data from the UD_English-EWT directory.
"""
import conllu, fileinput, sys, glob

SENTIDS = 'ewt_ud.sentids'
if __name__=='__main__':
    SENTIDS = sys.argv[1]

EWTSRC = [f'/Users/nathan/dev/nlp-tools/UD_English/en_ewt-ud-{part}.conllu' for part in ['train','dev','test']]

alltrees = {}

for udFP in EWTSRC:
    with open(udFP, encoding='utf-8') as udF:
        sents = conllu.parse(udF.read())
        for sent in sents:
            alltrees[sent.metadata['sent_id']] = sent

for ln in fileinput.input(SENTIDS):
    sentid = ln.strip().split()[-1]
    sent = alltrees[sentid]
    print(sent.serialize(), end='')
