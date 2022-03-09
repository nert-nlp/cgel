import stanza
from stanza.utils.conll import CoNLL

nlp = stanza.Pipeline(lang='en', processors='tokenize,mwt,pos,lemma,depparse', tokenize_no_ssplit=True)

sents = []
with open('sentences_fixed.txt', 'r') as fin:
    for row in fin:
        row = row.strip()
        sents.append(row)

doc = nlp('\n\n'.join(sents))
CoNLL.write_doc2conll(doc, 'sentences_fixed.conllu')