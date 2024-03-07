"""
Given a .docx file containing numbered examples from the CGEL manuscript,
and the CGEL book PDF, print examples augmented with page numbers.
"""
from pypdf import PdfReader
import glob
import docx
import sys
import re

import unicodedata

reCATS = re.compile(r'^((NP?|VP?|VGp|DP?|PP?|Prep|AdjP?|AdvP?|Clause(rel|REL)?[12]?|Nom|Quantifier|Coordinator)(interrog)?(-coordination)?\+?((gap)?i)?)+$')
reFXNS = re.compile(r'^((Head|Mod(ifier)?|P(redicator)?|Predicate|Comp[12]?|PredComp|Nucleus|Prenucleus|Subj(ect)?|O(bj(ect)?)?[12]?|Det|Det-Head|Mod-Head|Subj-det|Subj-det-Head|PredicatorPredComp|Marker|Coordinate[12]|Supplement):)+$')
reTreeHeader = re.compile(r'^\[\d+\]a\.(Clause|NP|NPinterrog|PP|VP)b\.(Clause|NP|NPinterrog|PP|VP)(c\.(Clause|NP|NPinterrog|PP|VP))?$')
reNUMERICEX = re.compile(r'^\[\d+\]')
reSENTTERMINAL = re.compile(r'(((?<!etc)\.)|[!?])\'?(\t|$|\]| \(e.g.| \[sc. )')
#rePHRASELIKE = re.compile(r"^(\[[0-9]+\]\t)?\t[ivx]*\t([a-z]\.)?\t[*%#!]?\[?[\w'-]+ [\w/'-]+ [\w/'\[-]+")  # captures a lot of phrases/sentences not captured by reSENTTERMINAL
# rePHRASELIKE captures a lot of phrases/sentences not captured by reSENTTERMINAL
rePHRASELIKE = re.compile(r"^(A: )?[*%#!?]?\[?"
                          r"([\w`'-]|/ ?[*%#!?]?\w|-\[)+\]? "   # 1st word
                          r"\[?([\w/`'-]|/ ?[*%#!?]?\w|-\[)+\]? "   # 2nd word
                          r"\[?(a|I|([\w/`'\[-]|/ ?[*%#!]?\w|-\[){2,})")  # 3rd word
rePHRVERBLIKE = re.compile(r"^[*%#!?]?\[?[a-z'-]+ (the )?("
                           r"[a-z/'-]+ (against|as|down|for|in|of|on|out|to|with|p|f)( [pf])?(\t|$)"
                           r"|"
                           r"(against|as|down|for|in|of|on|out|to|up|with) \[[a-z]"
                           r")")

reLI = re.compile(r'(^\[[0-9A-Z]+\](?=\t))|\t[xvi]+(?=\t)|\t([a-z])\.(?=\t)')

JUST_SENTENCES = True

def normalize_text(text):
    text = unicodedata.normalize('NFKD', text)  # handles things like fi ligatures
    return ''.join([c for c in text if not unicodedata.combining(c)]).replace("’", "'")

def extract_paragraphs_from_docx(docx_path):
    doc = docx.Document(docx_path)
    paragraphs = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            paragraphs.append(paragraph.text)
    return paragraphs

def extract_pdf_pages(pdf_path):
    FRONT_MATTER_OFFSET = 19    # 19 pages of front matter
    with open(pdf_path, 'rb') as pdf_file:
        pdf_reader = PdfReader(pdf_file)
        for i,page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            logical_page_num = i - FRONT_MATTER_OFFSET
            yield logical_page_num,page_text

RE_TABFIX1 = re.compile(r'(\t[a-z]\.) ')
RE_TABFIX2 = re.compile(r' ([xvi]+\t)')
def clean_excerpt(excerpt):
    return normalize_text(excerpt).replace(' ','').replace('\t','').replace('|','').replace('_','').replace('“','').replace('”','').replace('–','').replace('↗','').replace('↘','')

def clean_page_text(text):
    return normalize_text(text).replace(' ','').replace('\n','').replace('|','').replace('∗','*').replace('·','').replace('“','').replace('”','').replace('‘','`').replace('∼','').replace('–','').replace('↗','').replace('↘','')

def main(docx_path, pdfI):
    docx_paragraphs = extract_paragraphs_from_docx(docx_path)
    last_match = 0
    page_num,page_text = next(pdfI)
    cleaned_page_text = clean_page_text(page_text)
    for i,excerpt in enumerate(docx_paragraphs):

        # fix a couple of formatting inconsistencies
        excerpt = RE_TABFIX1.sub(r'\1\t', excerpt) # space after alphabetic label should be tab
        excerpt = RE_TABFIX2.sub(r'\t\1', excerpt)  # space before roman numeral label should be tab
        excerpt = excerpt.replace(' \t', '\t')

        # TODO "a few examples ending in "etc." that are now not being matched. What about allowing ", etc." to be matched if not plain "etc."?"
        #  https://github.com/nert-nlp/cgel/commit/613a8c2a6d0c462588b3db017d710006acb8ab70#r136014168
        if not reSENTTERMINAL.search((q := reLI.sub('\t', excerpt).replace('\t)', '\t').replace('(\t', '\t').strip())) and not rePHRASELIKE.search(q):
            prefix = '!'    # doesn't look like a real sentence (perhaps a word list, tree, table, or example heading)
            #assert False,q
        elif (not reSENTTERMINAL.search(q)) and rePHRASELIKE.search(q) and rePHRVERBLIKE.search(q):
            prefix = '!'    # e.g. "cash in on"
        elif q.startswith(('Oi ','S ','goal ','theme ','quest ','restrictions ','version with', 'variable as')) \
            or q.endswith((' as object',)) or ' '.join(q.split()[1:3]) in {'adj inf','np inf'}:
            prefix = '!'    # e.g. header row
        elif q==excerpt.replace('\t)', '\t').replace('(\t', '\t').rstrip():
            # no label
            #assert 'stand by p f' not in q,(not reSENTTERMINAL.search(q), rePHRASELIKE.search(q), rePHRVERBLIKE.search(q))
            prefix = '@'
        else:
            # if rePHRASELIKE.search(q) and not reSENTTERMINAL.search(q):
            #     print(q, file=sys.stderr)
            prefix = '#'

        cleaned_excerpt = clean_excerpt(excerpt)

        if not any(c.isalpha() for c in cleaned_excerpt):
            continue    # not a real example
        elif cleaned_excerpt.startswith("[1]ia.Hedidn'treadthereport,noteventhesummary."):
            cleaned_excerpt = cleaned_excerpt[3:]   # there is an extra heading in the PDF
        elif cleaned_excerpt[2:].startswith(("Hedidn'treadthereport","Hedidn'treadit")):
            cleaned_excerpt = cleaned_excerpt[2:]
        # elif cleaned_excerpt=='HeisillHead:Predicator:PredComp':
        #     cleaned_excerpt = 'Heisill'
        elif cleaned_excerpt in ['writingnow', '[11]NP', '[4]Clause']:
            print(f"{prefix}___| {excerpt}")
            continue
        elif '<T/T' in cleaned_excerpt or 'Tr<To/Td' in cleaned_excerpt or '[46]VP' in cleaned_excerpt:
            print(f"{prefix}___| {excerpt}")
            continue
        elif reTreeHeader.match(cleaned_excerpt) or reCATS.match(cleaned_excerpt) or reFXNS.match(cleaned_excerpt):
            print(f"{prefix}___| {excerpt}")
            continue    # tree

        #print('>>', cleaned_excerpt, file=sys.stderr)
        while True: # loop over pages
            # if the example is numbered, is the number missing from the page? (to avoid suffix match false positives)
            m = reNUMERICEX.match(cleaned_excerpt)
            numericMismatch = m and m.group(0) not in cleaned_page_text
            if numericMismatch and (rest := cleaned_excerpt[len(m.group(0)):]) in cleaned_page_text:
                # looks like example numbers differ - a mismatch between docx and PDF (a few are typos in the PDF)
                if cleaned_excerpt=="[13]iShedoesn'tsitandmopebut(rather)makesthebestofthesituation.":
                    cleaned_excerpt = '[14]'+cleaned_excerpt[4:]    # PDF p. 737 has no example [13] and two [14]s
                elif cleaned_excerpt=='[12]ia.#IfIamyouIwillaccepttheoffer.b.IfIwereyouIwouldaccepttheoffer.':
                    cleaned_excerpt = '[11]'+cleaned_excerpt[4:]    # PDF p. 742 has no example [12] and two [11]s
                elif cleaned_excerpt=='[42]iHewouldgetadistinctionifonlyhewouldbuckledowntosomehardwork.':
                    cleaned_excerpt = '[12]'+cleaned_excerpt[4:]    # PDF p. 751 has [12] instead of [42]
                else:
                    assert not re.search(r'\[\d+\]' + re.escape(rest), cleaned_page_text),(cleaned_excerpt, page_num, cleaned_page_text)
            if cleaned_excerpt.startswith('[1]icomplementsThemostcentralprepositions'):
                cleaned_excerpt = '[9]'+cleaned_excerpt[3:]     # PDF p. 603 has a repeated [9] that should be [1]
            elif cleaned_excerpt=='[17]complexsimple':
                cleaned_excerpt = '[17complexsimple'    # PDF p. 1205 has example number missing bracket

            if cleaned_excerpt in cleaned_page_text:
                print(f"{prefix}{page_num}| {excerpt}")
                cleaned_page_text = cleaned_page_text[cleaned_page_text.index(cleaned_excerpt)+len(cleaned_excerpt):]
                break
            elif len(cleaned_excerpt)>20 and cleaned_excerpt.lower() in cleaned_page_text.lower():
                # case mismatch e.g. small-caps
                print(f"{prefix}{page_num}| {excerpt}")
                i = cleaned_page_text.lower().index(cleaned_excerpt.lower())
                cleaned_page_text = cleaned_page_text[i+len(cleaned_excerpt):]
                break
            elif (len(cleaned_excerpt)>20 and cleaned_excerpt[:20].lower() in cleaned_page_text.lower()) \
                or cleaned_excerpt[:10] in cleaned_page_text and not cleaned_excerpt.startswith('primaryform') \
                or (cleaned_excerpt[-1]!=']' and cleaned_excerpt[-12:] in cleaned_page_text and not numericMismatch) \
                or (len(cleaned_excerpt)>20 and cleaned_excerpt[-20:] in cleaned_page_text and not numericMismatch):
                # partial match, maybe the line has some some special characters
                # "]" exception is to avoid false positive matches for repeated annotations like "[present tense]"
                print(f"{prefix}{page_num}| {excerpt}")
                break
            elif cleaned_excerpt in (SPECIAL := {'whatMaxsaidLizbought__': 49,
                                                 'Head:Predicator:PredComp': 50,    # missing colon in tree (also PDF)
                                                 'primaryform)finite': 89, 'plainform(imperative)': 89, '(infinitival)non-finite': 89,  # display with curly braces
                                                 '[18]haveortake': 295, # small caps
                                                 '[19]haveonly': 295, # small caps
                                                 '[20]takeonly': 295, # small caps
                                                 '[25]i(%his)[purportedlysex-neutralhe]': 492,   # parens vs. curly braces
                                                 'ii(%her)[purportedlysex-neutralshe]': 492,
                                                 'v(their)[singularthey]': 492,
                                                 'iv(his/her)[composite]': 492,
                                                 '[14]asktm(f)begtm(f)help(b)nspay(f)petition(f)': 1229,
                                                 '?ordertmpppermit': 1233,
                                                 '[42]feeltu(b)heartu(b)noticetubobservetu(b)overhear(b)': 1236,
                                                 'see1tu(b)watchb': 1236,
                                                 'prohibitbp?stop2': 1238,
                                                 'ii/se//sez//pe//ped//has//hazz//mni//mniz/': 1571,
                                                 '[4]i/hetd/hated/lændd/landed': 1573,
                                                 'ii/lft/laughed/hst/hissed': 1573,
                                                 'iii/lvd/loved/sted/stayed': 1573,
                                                 'iidose/dos//dosz/dosedoses': 1588,
                                                 'va./mas//mas/mousemice': 1589,
                                                 '[32]dig/dg//dg/digdug': 1603}):
                hardcoded_page = SPECIAL[cleaned_excerpt]
                if page_num==hardcoded_page:
                    prefix = '!'
                    print(f'{prefix}{hardcoded_page}| {excerpt}')
                    break
                # otherwise, wait till we get to the page
            elif i<len(docx_paragraphs)-1 and ((excerpt2 := clean_excerpt(docx_paragraphs[i+1])) in cleaned_page_text \
                or (excerpt2.startswith('[') and excerpt2[:10] in cleaned_page_text and not excerpt2.startswith('primaryform'))\
                or (len(excerpt2)>20 and excerpt2[:20].lower() in cleaned_page_text.lower())\
                or (excerpt2[-1]!=']' and excerpt2[-10:] in cleaned_page_text)):

                # if page_num==894 or page_num==869:
                #     print(cleaned_excerpt, '###', excerpt2, page_num, cleaned_page_text)

                if not numericMismatch: # if there is an example number not found on the current page, it's probably a false positive suffix match
                    print(f"{prefix}???| {excerpt}") # skip difficult-to-match excerpt; we know the next one matches
                    # if 'order' in excerpt:
                    #     print(cleaned_excerpt, cleaned_page_text, file=sys.stderr)
                    #     assert False
                    break

            # if page_num==1086:
            #     print(cleaned_excerpt, page_num, cleaned_page_text)

            page_num,page_text = next(pdfI)
            cleaned_page_text = clean_page_text(page_text)
            print(page_num, end='\n' if page_num%20==0 else ' ', file=sys.stderr)

            if last_match>0 and page_num-last_match>30: # looks like we're having trouble matching this example
                assert False,(cleaned_excerpt,)

        last_match = page_num

if __name__=='__main__':
    CGEL_PDF = 'cgel-clean.pdf'
    docxFPs = glob.glob('cge*.docx')
    docxFPs.sort()
    docxFPs = docxFPs[:16]   # skip ch. 18-20 for now (those are not really syntax anyway). note that ch1-2 are combined
    print(docxFPs)

    pdfI = extract_pdf_pages(CGEL_PDF)
    for docxFP in docxFPs:
        print('', file=sys.stderr)
        print(docxFP, file=sys.stderr, end='\n\n')
        main(docxFP, pdfI)
