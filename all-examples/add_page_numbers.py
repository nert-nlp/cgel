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

reCATS = re.compile(r'^((NP?|VP?|DP?|PP?|AdjP?|Clause)((gap)?i)?)+$')
reFXNS = re.compile(r'^((Head|Predicator|Predicate|Comp|PredComp|Nucleus|Prenucleus|Subject|Object|Det|PredicatorPredComp):)+$')

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

def clean_excerpt(excerpt):
    return normalize_text(excerpt).replace(' ','').replace('\t','')

def clean_page_text(text):
    return normalize_text(text).replace(' ','').replace('\n','').replace('∗','*').replace('·','')

def main(docx_path, pdfI):
    docx_paragraphs = extract_paragraphs_from_docx(docx_path)
    page_num,page_text = next(pdfI)
    for i,excerpt in enumerate(docx_paragraphs):
        # fix a couple of formatting inconsistencies
        excerpt = re.sub(r'(\t[a-c]\.) ', r'\1\t', excerpt) # space after alphabetic label should be tab
        excerpt = re.sub(r' ([xvi]+\t)', r'\t\1', excerpt)  # space before roman numeral label should be tab
        excerpt = excerpt.replace(' \t', '\t')

        if not re.search(r'[.!?](\t|$)', (q := reLI.sub('\t', excerpt).strip())):
            prefix = '!'    # doesn't look like a real sentence (perhaps a word list, tree, table, or example heading)
            #assert False,q
        elif q==excerpt:
            # no label
            prefix = '@'
        else:
            prefix = '#'

        cleaned_excerpt = clean_excerpt(excerpt)
        
        if not any(c.isalpha() for c in cleaned_excerpt):
            continue    # not a real example
        elif 'storm' in cleaned_excerpt and 'apparently' in cleaned_excerpt.lower():
            print(f"{prefix}___| {excerpt}")
            continue    # example modified in PDF
        elif cleaned_excerpt.startswith('[21]idativecase:') or cleaned_excerpt.startswith('iidativecase:'):
            #cleaned_excerpt = cleaned_excerpt.replace('dativecase', 'dative', 1)    # "case" removed in PDF
            pass
        elif cleaned_excerpt.startswith("[1]ia.Hedidn'treadthereport,noteventherecommendations."):
            cleaned_excerpt = cleaned_excerpt[3:]   # there is an extra heading in the PDF (and 'recommendations' was changed to 'summary')
        elif cleaned_excerpt[2:].startswith("Hedidn'treadthereport"):
            cleaned_excerpt = cleaned_excerpt[2:]
        elif cleaned_excerpt=='HeisillHead:Predicator:PredComp':
            cleaned_excerpt = 'Heisill'
        elif cleaned_excerpt in ['primaryform)finite', 'plainform(imperative)', 'writingnow']:
            print(f"{prefix}___| {excerpt}")
            continue
        elif '<T/T' in cleaned_excerpt or 'Tr<To/Td' in cleaned_excerpt:
            print(f"{prefix}___| {excerpt}")
            continue
        elif (x := cleaned_excerpt.replace('|','')) in ['[13]a.NPb.NP', '[5]a.Clauseb.Clause', '[8]a.Clauseb.Clause'] or reCATS.match(x) or reFXNS.match(x):
            print(f"{prefix}___| {excerpt}")
            continue    # tree

        print('>>', cleaned_excerpt, file=sys.stderr)
        while True: # loop over pages
            cleaned_page_text = clean_page_text(page_text)

            # if page_num==84:
            #     print(cleaned_page_text, file=sys.stderr)
            
            if cleaned_excerpt in cleaned_page_text:
                print(f"{prefix}{page_num}| {excerpt}")
                cleaned_page_text = cleaned_page_text[cleaned_page_text.index(cleaned_excerpt)+len(cleaned_excerpt):]
                break
            elif cleaned_excerpt[:10] in cleaned_page_text and not cleaned_excerpt.startswith('primaryform') \
                or (cleaned_excerpt[-1]!=']' and cleaned_excerpt[-12:] in cleaned_page_text):
                # partial match, maybe the line has some some special characters
                # "]" exception is to avoid false positive matches for repeated annotations like "[present tense]"
                print(f"{prefix}{page_num}| {excerpt}")
                break
            elif (excerpt2 := clean_excerpt(docx_paragraphs[i+1])) in cleaned_page_text \
                or (excerpt2[:10] in cleaned_page_text and not excerpt2.startswith('primaryform'))\
                or excerpt2[-10:] in cleaned_page_text:
                print(f"{prefix}???| {excerpt}") # skip difficult-to-match excerpt; we know the next one matches
                break

            if page_num==216 and cleaned_excerpt=='CPCC':
                assert False,(cleaned_excerpt, page_num, cleaned_page_text)

            page_num,page_text = next(pdfI)
            print(page_num, file=sys.stderr)

            if page_num>300:
                assert False,(cleaned_excerpt,)

if __name__=='__main__':
    CGEL_PDF = 'cgel-clean.pdf'
    docxFPs = glob.glob('cge*.docx')
    docxFPs.sort()
    print(docxFPs)

    pdfI = extract_pdf_pages(CGEL_PDF)
    for docxFP in docxFPs:
        print('', file=sys.stderr)
        print(docxFP, file=sys.stderr, end='\n\n')
        main(docxFP, pdfI)
