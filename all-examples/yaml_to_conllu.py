import re
import yaml
from yaml import CLoader as Loader
import collections
from pagified_html_to_yaml import RE_END_TAG
from bs4 import BeautifulSoup
import stanza
from stanza.utils.conll import CoNLL

rePUNCT = re.compile(r'([.?!])')
RE_PRETAG = re.compile(r'<(small-caps|strong)>[a-z0-9\- <>\/]+</(small-caps|strong)>')


def get_nested_sentences(nested_dict):
    """
    returns a tuple of (id, line) for each example in the nested dictionary
    """
    for value in nested_dict.values():
        if isinstance(value, dict):
            yield from get_nested_sentences(value)
        elif type(value) == list:  # ignore page numbers
            yield value


def clean_sentence(sent):
    posttag = re.search(RE_END_TAG, sent)
    if posttag is not None:
        posttag = posttag.group()
    sent = re.sub(RE_END_TAG, '', sent)
    pretag = re.match(RE_PRETAG, sent)
    if pretag is not None:
        pretag = pretag.group()
        sent = sent.replace(pretag, '')
        pretag = BeautifulSoup(pretag, features="lxml").get_text()
    status = re.match(r'[*#%?!]', sent)
    if status is not None:
        status = status.group()
        sent = sent[1:]

    sent = re.sub(r'<sub>[a-z]+</sub>', '', sent)

    sent = BeautifulSoup(sent, features="lxml").get_text()

    # special cases chapter 1-2
    sent = sent.replace('to-infinitival', '')  # mix of html tags causing trouble parsing
    sent = sent.replace('(preterite', '')  # from p. 50 example formatting

    if '/' in sent:  # sentences split with '/'
        # TODO actual handling for adding the split sentences to the conllu
        # manually added for cge01-02Ex
        # planned to have a dictionary of format { "sentence a/b" : [sentence a, sentence b] } to use for handling, created from splits.html
        return
    subs = re.split(rePUNCT, sent)
    # print(subs)
    if len(subs) > 3:  # multi-sentence lines
        sent = re.sub(r'([a-z])\.([A-Z])', r'\1.\n\2', sent)
    else:
        sent = "".join(subs[0:2])

    sent = sent.replace('\t', '').replace('[', '').replace(']', '').replace('__', '').replace(' .', '.').replace('`', '\'')
    return sent, status, posttag, pretag


if __name__ == '__main__':
    outfile = "cge01-02Ex.conllu"  # change to desired output filename
    f_yaml = open('cge01-02Ex.yaml', 'r', encoding="utf-8") # change to desired yaml input
    y = yaml.load(f_yaml, Loader=Loader)
    sents = list(get_nested_sentences(y))

    nlp = stanza.Pipeline(lang='en', processors='tokenize,mwt,pos,lemma,depparse', package='ewt')

    cleans = []

    with open('temp.conllu', 'w', encoding="utf-8") as f:
        pass

    # with open('cge01-02.conllu', 'w', encoding='utf-8') as f:
    #     f.write('# The following symbols indicate the status of examples (in the interpretation under consideration):\n')
    #     f.write('# * ungrammatical *This books is mine.\n')
    #     f.write('# # semantically or pragmatically anomalous #We frightened the cheese.\n')
    #     f.write('# % grammatical in some dialect(s) only %He hadn’t many friends.\n')
    #     f.write('# ? of questionable grammaticality ?Sue he gave the key.\n')
    #     f.write('# ! non-standard !I can’t hardly hear.\n')

    ids = []
    for s in sents:
        cs = clean_sentence(s[1])
        if cs is not None:
            sid = s[0]
            sid = sid.replace('.', '')  # .replace('[', '').replace(']', '')
            ids.append(sid)

            cleans.append(cs)
            doc = nlp(cs[0])

            for i in range(1, len(doc.sentences)):
                ids.append(sid)

            with open('temp.conllu', 'a', encoding="utf-8") as f:

                f.write('# formatted_line = ' + s[1] + '\n')
                if cs[1] is not None:
                    f.write('# status = ' + cs[1] + '\n')
                if cs[2] is not None:
                    f.write('# posttag = ' + cs[2] + '\n')
                if cs[3] is not None:
                    f.write('# pretag = ' + cs[3] + '\n')

            CoNLL.write_doc2conll(doc, 'out.conllu', 'a', encoding='utf-8')

            if cs[1] is not None:
                print(cs[1], cs[0])
            else:
                print(cs[0])

            if cs[2] is not None:
                print(cs[2])

    c = 0
    for idx, sid in enumerate(ids):
        if idx > 0:
            if sid == ids[idx-1]:
                print(sid + " = " + ids[idx-1])
                print("setting " + ids[idx-1] + " to " + ids[idx-1] + '_' + str(c))
                ids[idx-1] = ids[idx-1] + '_' + str(c)
                c += 1
            else:
                if c > 0:
                    print("setting " + ids[idx - 1] + " to " + ids[idx-1] + '_' + str(c))
                    ids[idx - 1] = ids[idx-1] + '_' + str(c)
                c = 0
    if c > 0:
        ids[-1] = ids[-1] + '_' + str(c)
    i = 0


    with open('x.conllu', 'a', encoding="utf-8") as f:
        if cs is not None and cs[1] is not None:
            f.write('# status = ' + cs[1] + '\n')
        if cs is not None and cs[2] is not None:
            f.write('# posttag = ' + cs[2])
        with open('out.conllu', 'r', encoding="utf-8") as o:
            for line in o.readlines():
                if "# sent_id = " in line:
                    if i < len(ids):
                        print(ids[i])
                        line = re.sub(r'(# sent_id = )([0-9])', r'\1' + ids[i], line).replace('\\', '')
                    i += 1

                f.write(line)
