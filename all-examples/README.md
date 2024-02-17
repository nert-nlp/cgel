This folder contains all the numbered examples in the _Cambridge Grammar of the English Language_ (CGEL). They appear in .doc format by chapter, extracted manually from the manuscript. The page numbers and section numbers have been stripped, so numbers are typically non-unique. For example, in chapter 3, there are eight distinct examples given as `[1]`.

The .doc files were then converted to .docx files and matched against the book PDF to obtain page numbers for the examples. (A few modifications were made in the .docx files where the PDF differed.) The `add_page_numbers.py` script performs the alignment; the output of the script is in `pagified`. Because of noise in how things are encoded in .docx vs. .pdf, not every line could be mapped definitively.

An excerpt from `pagified`, which contains the page-aligned output for examples in chapters 1-17:

```
#47|    v       a.      If it hadn't been for you, I    b.      *It had been for you.
@47| couldn't have managed.
#48| [4]                        a.      Liz bought a watch.     b.      I wonder what Liz bought.
!___| [5]                       a.                      Clause                                          b.                      Clause
!___|                           Subject:                        Predicate:                              Prenucleus:                     Nucleus:
!___|                           NP                      VP                                              NPi                     Clause
!___|                           Head:           Predicator:             Object:                 Head:           Subject:                        Predicate:
!___|                           N               V                       NP                              N               NP                      VP
!___|                                                           Det:            Head:                                   Head:   Predicator:     Object:
!___|                                                           D               N                                       N       V               gapi
!???|                           Kim             bought          a               watch                   what            Kim     bought          __
#49| [6]                                I can't remember [what Max said Liz bought __].
```

Every line begins with a prefix, a page number or placeholder, `|`, and a space. The rest of the line is a paragraph directly from the .docx file, minus formatting. Note that some special symbols use an odd (non-Unicode) character encoding and will not appear. Additional work will be required to retain formatting present in the .docx such as subscripts/superscripts, small-caps, underlining, and boldface.

The prefix uses heuristics to determine the nature of the line. Lines that appear to contain at least one full sentence and a numeric label (like `[1]` or `i`) begin with `#`. Lines that appear to contain the end of a sentence, but lack a numeric label, begin with `@`: often these are continuations of the textual part of an example in a previous line. The other lines have prefix `!`; these may be word lists, trees, long sentences whose endings wrap to the next line, etc.

The script recognizes the nonlexical material in trees and avoids matching it (sometimes the line contains simply `NP VP` or similar, which could lead to false positive matches), instead giving the placeholder `___`. A placeholder of `???` indicates that the line could not be matched (possibly due to special characters or changes to the example) but the subsequent line could, so by looking at context it is usually possible to narrow it down to 1 or 2 pages.

'pagified.html' contains the page-aligned output from add_html_formatting.py with html formatting extracted from .docx files using the Mammoth library.

Universal Dependencies parses found in the .conllu files are generated using the dev branch of Stanza as of 12/31/2023 and manually edited.