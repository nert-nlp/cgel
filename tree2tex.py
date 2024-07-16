"""
Convert a CGEL tree to LaTeX (forest package).
Most of the implementation is in cgel.py.

@author: Nathan Schneider (@nschneid)
@since: 2022-07-29
"""

import re, sys
from itertools import chain
from typing import Iterable
import cgel

r""" fusion (new style):
(x / NP
    :Head (Nom
        :Det-Head (DP
            :Head (D :t "what"))))
"Det-Head" is understood as implying a (Det) edge under the grandparent, before the head.
Similarly for Head-Prenucleus (prenucleus follows head) and Mod-Head, Marker-Head.

[\small\textsf{Obj:}\\NP
        [\small\textsf{Head:}\\Nom,before drawing tree={x+=2em}
		    [\small\textsf{Det-Head:}\\DP, no edge
			[this, roof]
			] {
			    \draw[-] (!uu.south) -- ();
			    \draw[-] (!u.south) -- ();
			  }
		]]
"""


# file header -- forest package
HEADER = r'''
\documentclass[tikz,border=12pt]{standalone}
\usepackage[linguistics]{forest}
\usepackage{times}
\usepackage{textcomp}
\usepackage{xcolor}
\usepackage{soul}
\usepackage[T1]{fontenc}
\usepackage{marvosym}

\definecolor{orange}{HTML}{FFCCFF}
\definecolor{ltyellow}{HTML}{FFFFAA}
\definecolor{cgelblue}{HTML}{009EE0}

% text highlight color
% https://tex.stackexchange.com/a/352959
\newcommand{\hlc}[2][yellow]{{%
    \colorlet{foo}{#1}%
    \sethlcolor{foo}\hl{#2}}%
}
\newcommand{\hlgreen}[2][green]{{%
    \colorlet{foo}{#1}%
    \sethlcolor{foo}\hl{#2}}%
}
\newcommand{\p}[1]{%
    \sethlcolor{white}\color{gray}\hl{#1}%
}

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
\newcommand{\idx}[1]{\textsubscript{\fcolorbox{red}{white}{\textcolor{red}{#1}}}}
%----------------------------------------------------------------------
\begin{document}
'''

FOOTER = '''
\\end{document}
'''

def trees2tex(trees: Iterable[cgel.Tree]) -> str:
    i = 0
    s = HEADER + '\n'
    for tree in trees:
        #s = tree.draw()
        for k,v in tree.metadata.items():
            s += f'% # {k} = {v}\n'
        s += tree.drawtex() + '\n'
        #break # just print one tree
        i += 1
    s += FOOTER
    return s

def main(cgelFP: str):
    with open(cgelFP) as f2:
        print(trees2tex(tree for tree in cgel.trees(chain(f2))))

if __name__=='__main__':
    main(sys.argv[1])
