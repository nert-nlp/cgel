import glob
import re
import mammoth
from bs4 import BeautifulSoup

from add_page_numbers import normalize_text, RE_TABFIX1, RE_TABFIX2

RE_LINE_TAG = re.compile(r'^[#@!]([0-9]+|\?\?\?|___)\| ')
RE_ALPHA = re.compile(r'[a-zA-Z]')

RE_FOOTNOTE = re.compile(r'(footnote(-ref)?-[0-9]+)')
footnote_fixer = 0


def format_html_lines(html):
    return html.replace('</p><p>', '</p>\n<p>').replace('</ol>', '</ol>\n').replace('</p><ol>', '</p>\n<ol>').replace(
        '</p><table>', '</p>\n<table>').replace('</table><p>', '</table>\n<p>')


def main(html_text, pagified_lines):
    curr_line = 1  # assuming the first line in pagified is a list of docxFPs
    html_lines_pagified = []
    html_lines_pagified.append(html_text.partition('\n')[0])  # handle first line of docxFPs

    for idx, line in enumerate(html_text.splitlines()[1:]):  # skipping line of docxFPs

        if re.search(RE_ALPHA, BeautifulSoup(line, "lxml").text) is None:  # no alphabet characters, ignoring html tags
            continue
        elif line[:2] != '<p':  # mammoth extracts extra footnotes and tables; ignore these
            continue
        else:
            prefix = re.match(RE_LINE_TAG, pagified_lines[curr_line])
            html_lines_pagified.append(line.replace('<p>', '<p>' + prefix.group(), 1)
                                       .replace('<span>', '<span style="font-variant: small-caps;">'))
            curr_line += 1

    full_html_pagified = '\n'.join(html_lines_pagified)
    # full_html_pagified = re.sub('</p>\n<p>@', '\n<br>@', full_html_pagified)

    with open("pagified.html", "w", encoding="utf-8") as f:
        f.write(full_html_pagified)


if __name__ == '__main__':
    pagified = open('pagified', 'r')
    pagified_lines = pagified.readlines()
    docxFPs = glob.glob('cge*.docx')
    docxFPs.sort()
    docxFPs = docxFPs[:16]  # skip ch. 18-20 for now (those are not really syntax anyway). note that ch1-2 are combined

    html_list = []

    docxFPs_html = ''.join(['<p>', str(docxFPs), '</p>'])
    html_list.append(docxFPs_html)

    style_map = """
    u => u
    small-caps => span
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
