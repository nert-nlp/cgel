"""
Convert a CGEL tree to LaTeX.

Not yet supported: fused heads

@author: Nathan Schneider (@nschneid)
@since: 2022-07-29
"""

import re, sys
from itertools import chain
from pylatexenc.latexencode import unicode_to_latex
import cgel

def latex_quote(s, dialect):
    if dialect=='parsetree':
        return unicode_to_latex(s).replace("'", r'\textquoteright{}').replace("`", r'\textquoteleft{}')
    else:
        return unicode_to_latex(s).replace(',', '{,}')  # forest package doesn't like unescaped commas in terminals for some reason

# Example tree
r'''
(.Clause.
    (.\NL{Subj}{NP}.
        (.\NL{Head}{Nom}.
            (.\NL{Head}{N}. `it')))
    (.\NL{Head}{VP}.
        (.\NL{Head}{V}. `\textquoteright s' )
        (.\NL{PredComp}{AdjP}.
            (.\NL{Head}{Adj}. `alright' )))
    (.\NL{ExtraposedSubject}{Clause}.
        (.\NL{Head}{VP}.
            (.\NL{Marker}{Subordinator}. `to' )
        (.\NL{Head}{VP}.  `say they\textquoteright re white' )
)))
'''

QTD = r'"(?:[^"\\]|\\"|\\\\)*"'
def cgel2tex(s: str, dialect='forest' or 'parsetree') -> str:
    t = re.sub(r' (:p|:l|:subt|:subp|:note) '+QTD, '', s)   # remove punctuation, lemmas, subtokens, notes
    t = t.replace('N_pro', r'N\textsubscript{\textsc{pro}}')
    t = t.replace('V_aux', r'V\textsubscript{\textsc{aux}}')
    t = t.replace('Clause_rel', r'Clause\textsubscript{rel}')
    t = t.replace('Obj_dir', r'Obj\textsubscript{dir}')
    t = t.replace('Obj_ind', r'Obj\textsubscript{ind}')
    t = t.replace('Comp_ind', r'Comp\textsubscript{ind}')
    assert '_' not in t,t
    t = re.sub(r'\bGAP(?=\))',
                r'GAP :t "--"', t)  # add -- terminal for gap
    if 'GAP' in s:
        assert '--' in t,s
    t = re.sub(r'([^\s"\)])(?=\)+($|\n))',
                r'\1 :t ""', t)  # other childless nonterminal with no string (due to fusion)
    t = re.sub(r'(\s+):(\S+) \((\S+) / ([^\s\)]+)',
                r'\1:\2 (\4\\textsubscript{\3}', t) # coindexation subscript
    if dialect=='parsetree':
        t = re.sub(r'^\((\S+)', r'(.\1.', t)    # root
        t = re.sub(r'(\s+):(\S+) \(([^\s\)]+)',
                    r'\1(.\\NL{\2}{\3}.', t)    # non-root nonterminal
        t = re.sub(r'( :t ('+QTD+'))? :correct ('+QTD+')',    # token with correction
                    lambda m: "  `"+latex_quote(cgel.cgel_unquote(m.group(2) or '""') + ' [' + cgel.cgel_unquote(m.group(3)) + ']', dialect) + "'", t)
        t = re.sub(r' :t ('+QTD+')',    # token
                    lambda m: "  `"+latex_quote(cgel.cgel_unquote(m.group(1)), dialect)+"'", t)
    else:
        u = re.sub(r'\)(?=\]*($|\n))', ']', t)  # trailing brackets on a line
        while u!=t:
            t = u
            u = re.sub(r'\)(?=\]*($|\n))', ']', t)  # trailing brackets on a line
        t = re.sub(r'^\((\S+)', r'[\1', t)    # root
        t = re.sub(r'(\s+):(\S+) \(([^\s\)]+)',
                    r'\1[\\Node{\2}{\3}', t)    # non-root nonterminal
        t = re.sub(r'( :t ('+QTD+'))? :correct ('+QTD+')',    # token with correction
                    lambda m: "["+latex_quote(cgel.cgel_unquote(m.group(2) or '""') + ' (' + cgel.cgel_unquote(m.group(3)) + ')', dialect) + "]", t)
        t = re.sub(r' :t ('+QTD+')',    # token
                    lambda m: "["+latex_quote(cgel.cgel_unquote(m.group(1)), dialect)+"]", t)
    return SHEADER[dialect] + t + SFOOTER[dialect]

# header for parsetree dialect
PHEADER = r'''
\documentclass[12pt]{standalone}
\usepackage{times}
\usepackage{parsetree}
\usepackage{textcomp}
\pagestyle{empty}
%----------------------------------------------------------------------
% Node labels in CGEL trees are defined with \NL, which is defined so that
% \NL{Abcd}{Xyz} yields a label with the function Abcd on the top, in
% sanserif font, followed by a colon, and the category Xyz on the bottom.
\newcommand{\NL}[2]{\begin{tabular}[t]{c}\small\textsf{#1:}\\
#2\end{tabular}}
%----------------------------------------------------------------------
\begin{document}
'''

# header for forest dialect
FHEADER = r'''
\documentclass[tikz,border=12pt]{standalone}
\usepackage[linguistics]{forest}
\usepackage{times}
\usepackage{xcolor}
\usepackage[T1]{fontenc}
\pagestyle{empty}
%----------------------------------------------------------------------
% Node labels in CGEL trees are defined with \Node,
% which is defined so that \Node{Abcd}{Xyz} yields
% a label with the function Abcd on the top, in small
% sanserif font, followed by a colon, and the category
% Xyz on the bottom.
\newcommand{\Node}[2]{\small\textsf{#1:}\\{#2}}
% For commonly used functions this is defined with \(function)
\newcommand{\Head}[1]{\Node{Head}{#1}}
\newcommand{\Subj}[1]{\Node{Subj}{#1}}
\newcommand{\Comp}[1]{\Node{Comp}{#1}}
\newcommand{\Mod}[1]{\Node{Mod}{#1}}
\newcommand{\Det}[1]{\Node{Det}{#1}}
\newcommand{\PredComp}[1]{\Node{PredComp}{#1}}
\newcommand{\Crd}[1]{\Node{Coordinate}{#1}}
\newcommand{\Mk}[1]{\Node{Marker}{#1}}
\newcommand{\Obj}[1]{\Node{Obj}{#1}}
\newcommand{\Sup}[1]{\Node{Supplement}{#1}}
%----------------------------------------------------------------------
\begin{document}
'''

SHEADER = {'parsetree': r'''
\begin{parsetree}
''', 'forest': r'''
\begin{forest}
where n children=0{% for each terminal node
    font=\itshape, 			% italics
    tier=word          			% align at the "word" tier (bottom)
  }{%								% no false conditions, so empty
  },
'''}

SFOOTER = {'parsetree': r'''
\end{parsetree}
''', 'forest': r'''
\end{forest}
'''}

FOOTER = '''
\end{document}
'''

if __name__=='__main__':
    dialect = 'forest'
    with open('datasets/twitter.cgel') as f, open('datasets/ewt.cgel') as f2:
        i = 0
        print(PHEADER if dialect=='parsetree' else FHEADER)
        for tree in cgel.trees(chain(f,f2)):
            s = tree.draw()
            if i>=85:
                for k,v in tree.metadata.items():
                    print(f'% # {k} = {v}')
                print(cgel2tex(s, dialect=dialect))
            i += 1
            if i>=100: break
        print(FOOTER)
