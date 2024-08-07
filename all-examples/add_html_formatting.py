import glob
import re
import sys
import mammoth
from bs4 import BeautifulSoup

from add_page_numbers import normalize_text, RE_TABFIX1, RE_TABFIX2

RE_LINE_TAG = re.compile(r'^[#@!]([0-9]+|\?\?\?|___)\| ')
RE_ALPHA = re.compile(r'[a-zA-Z]')

RE_FOOTNOTE = re.compile(r'(footnote(-ref)?-[0-9]+)')

def format_html_lines(html):
    return html.replace('</p><p>', '</p>\n<p>').replace('</ol>', '</ol>\n').replace('</p><ol>', '</p>\n<ol>').replace(
        '</p><table>', '</p>\n<table>').replace('</table><p>', '</table>\n<p>')


def main(html_text, pagified_lines, outFP="pagified.html"):
    line_count = 1  # line number, assuming the first line in pagified is a list of docxFPs
    html_lines_pagified = []
    html_lines_pagified.append('<head> <link rel="stylesheet" href="style.css"> </head>')
    html_lines_pagified.append(html_text.partition('\n')[0])

    group = None

    for line in html_text.splitlines()[1:]:
        if re.search(RE_ALPHA, BeautifulSoup(line, "lxml").text) is None:
            continue
        elif line[:3] != '<p>':  # ignore extra footnotes and tables extracted by mammoth
            continue
        else:
            prefix = re.match(RE_LINE_TAG, pagified_lines[line_count])
            p = prefix.group()
            if (c := p[0])=='@':
                #assert 'small-caps>' not in line,(prefix.group(),line)
                if c0=='!' and '\t' in line and '???' not in p: #'</em>' in line.split('\t')[-1]:
                    group = 'tabular'   # table without column subnumbers
                if group=='tabular':
                    p = '#' + p[1:]
            elif c=='!':
                group = '!'
            elif c=='#':
                group = '#'
            line = line.replace('<p>', '<p>' + p, 1)

            c0 = c

            line_count += 1 + line.count('<br />')  # ch. 3 p. 130 has <br /> line breaks within text
            print(line)
            html_lines_pagified.append(line)

    full_html_pagified = '\n'.join(html_lines_pagified)

    with open(outFP, "w", encoding="utf-8") as f:
        f.write(full_html_pagified + '\n')


if __name__ == '__main__':
    pagified = open('pagified', 'r', encoding="utf-8")
    pagified_lines = pagified.readlines()
    docxFPs = sys.argv[1:] or glob.glob('cge*.docx')
    docxFPs.sort()
    docxFPs = docxFPs[:16]  # skipping ch. 18-20

    html_list = []

    docxFPs_html = ''.join(['<p>', str(docxFPs), '</p>'])
    html_list.append(docxFPs_html)

    # "Double Underline" style was manually added to manuscripts for processing here
    style_map = """
    u => u
    small-caps => small-caps
    r[style-name='Double Underline'] => double-u
    """

    for docxFP in docxFPs:
        html = mammoth.convert_to_html(docxFP, style_map=style_map).value
        html = RE_TABFIX1.sub(r'\1\t', html)  # space after alphabetic label should be tab
        html = RE_TABFIX2.sub(r'\t\1', html)  # space before roman numeral label should be tab
        html = html.replace(' \t', '\t')
        html_list.append(html)

    full_html = ''.join(html_list)
    full_html = normalize_text(format_html_lines(full_html))  # text before is not normalized to NFKD

    main(full_html, pagified_lines)
