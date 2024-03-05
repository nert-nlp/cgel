# CGEL Examples Dataset

This folder contains all the numbered examples in the _Cambridge Grammar of the English Language_ (CGEL), as well as scripts for processing these examples.

The original examples appear in `.doc` format by chapter, extracted manually from the manuscript. The page numbers and section numbers have been stripped, so numbers are typically non-unique. For example, in chapter 3, there are eight distinct examples given as `[1]`.

A machine-readable version of sentential examples appears as a `.yaml` file. The file is suitable for loading e.g. with the PyYAML library, as illustrated in [stats.py](stats.py).

Currently, the YAML is limited to Chapters 1–13, but more chapters are forthcoming.
The YAML file provides globally unique IDs for top-level entries as well as sub-numbered examples.
It also indicates the page number in the book for each entry.

The YAML data and metadata can be found in:
- [cge01-13Ex.yaml](cge01-13Ex.yaml)
- CHAPTERS.yaml (chapter titles, authors, page ranges, and example number ranges; TODO)
- [STATS.md](STATS.md) (statistics on the extracted examples)

# Kinds of examples extracted in YAML

Most entries with a bracketed number, e.g. `[13]`, are included.
Many such entries have substructure—multiple sentential or phrasal items, with or without subnumbers: `i`, `ia`, etc.
Examples presented inline in body paragraphs are not included.

Formatting of example text is retained as HTML (with some custom tags). Linguistic material is italicized (typically within `<em>`...`</em>` tags; double-underlined material indicated with `<double-u>` is also italicized). Different kinds of emphasis and subscripts are also present, as well as metalinguistic markings like acceptability judgments (`*` etc.), square brackets for constituent structure, slashes for alternatives, and parentheses for optional material. See the explanation of notation... TODO

The YAML-extracted entries are focused on sentences and phrases. Here are some sample entries from Ch.&nbsp;14 with added comments:

```yaml
ex02880:
  page: '1255'
  '[19]':   # a simple example with an underlined portion
  - ex02880_p1255_[19]
  - <em>We've been giving <u>moving to Sydney</u> a good deal of thought recently.</em>
```

```yaml
ex02671:
  page: '1174'
  '[7]':    # 2 rows of sentences followed by row labels
    i:
    - ex02671_p1174_[7]_i   # full ID of [7i], which has multiple items without individual numbers
    - <em>Ed has</em> [<em>seen her</em>].  # bracketed constituent
    - <em>Ed has</em> [<em><u>been</u> seeing her</em>]<em>.</em>
    - <em>Ed has</em> [<em><u>been</u> seen</em>]<em>.</em>
    - <postTag>[perfect]</postTag>  # category assigned to the row
    ii:
    - ex02671_p1174_[7]_ii
    - <em>He had it</em> [<em>checked by the manager</em>]<em>.</em>
    - <postTag>[passive]</postTag>
```

```yaml
ex02896:
  page: '1260'
  '[16]':   # 3x2 structure: 3 rows (i-iii), 2 columns (a-b)
    i:
      a:
      - ex02896_p1260_[16]_i_a
      - <em>Kim <u>seemed</u> to be distressed.</em>    # a sentence
      b:
      - ex02896_p1260_[16]_i_b
      - '*<em>the <u>seeming</u> of Kim to be distressed</em>'  # a phrase; * = ungrammatical
    ii:
      a:
      - ex02896_p1260_[16]_ii_a
      - <em>I <u>believe</u> them to be genuine.</em>
      b:
      - ex02896_p1260_[16]_ii_b
      - '*<em>my <u>belief</u> in</em>/<em>of them to be genuine</em>'  # / for alternatives
    iii:
      a:
      - ex02896_p1260_[16]_iii_a
      - <em>They are <u>certain</u> to resent it.</em>
      b:
      - ex02896_p1260_[16]_iii_b
      - '*<em>their <u>certainty</u> to resent it</em>'
```

The following kinds of numbered entries are intentionally **omitted**:
- lexical lists
- pronunciations
- definitions
- semantic interpretations
- trees
- entries with special graphical formats

The presentation of examples often includes descriptive categories ("tags") before or after linguistic material.
The YAML data includes these as `<preTag>` and `<postTag>` items.

## Limitations

The extraction pipeline is not perfect; some (sub)examples are unintentionally included or excluded, or extracted with incorrect structure (e.g. missing `<postTag>`). The HTML for the extracted examples should be clean, however. Data cleanliness issues can be raised in the project issue tracker on GitHub.

The current extraction pipeline does not really parse the following features:
- dialogues with `A:` and `B:` interlocutors
- large curly braces indicating sharing across multiple examples
- headings for examples with column structure

Metalinguistic slashes and parentheses are retained; items containing them are not expanded into sets of full alternatives.

These are potential avenues for future improvement.

# Extraction pipeline

The `.doc` files were then converted to `.docx` files and matched against the book PDF to obtain page numbers for the examples. (A few modifications were made in the `.docx` files where the PDF differed, and to remove many of the items beyond sentence/phrase examples, such as definitions and footnotes.) The `add_page_numbers.py` script performs the alignment; the output of the script is in `pagified`. Because of noise in how things are encoded in `.docx` vs. `.pdf`, not every line could be mapped definitively.

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

Every line begins with a prefix, a page number or placeholder, `|`, and a space. The rest of the line is a paragraph directly from the `.docx` file, minus formatting. Note that some special symbols use an odd (non-Unicode) character encoding and will not appear.

The prefix uses heuristics to determine the nature of the line. Lines that appear to contain at least one full sentence or 3+-word phrase and a numeric label (like `[1]` or `i`) begin with `#`. Lines that appear to contain the end of a sentence, but lack a numeric label, begin with `@`: often these are continuations of the textual part of an example in a previous line. The other lines have prefix `!`; these may be word lists, long sentences whose endings wrap to the next line, column headers, etc.

The script recognizes the nonlexical material in trees and avoids matching it (sometimes the line contains simply `NP VP` or similar, which could lead to false positive matches), instead giving the placeholder `___`. A placeholder of `???` indicates that the line could not be matched (possibly due to special characters or changes to the example) but the subsequent line could, so by looking at context it is usually possible to narrow it down to 1 or 2 pages.

`pagified.html` contains the page-aligned output from `add_html_formatting.py` with HTML formatting extracted from `.docx` files using the Mammoth library. In addition to standard HTML tags like `<em>`, `<u>`, `<strong>`, and `<sub>`, this includes `<small-caps>` and `<double-u>`. `<double-u>` incorporates double underlining plus italics; its application disjoint from `<em>`, which applies to other cases of italics.

`pagified_html_to_yaml.py` produces the YAML, including sequential unique IDs for examples. (These can be removed with `strip_global_ex_ids.py` for cleaner comparison across versions of the data.)

`yaml_to_conllu.py` runs a dependency parser on the examples. Universal Dependencies parses found in the .conllu files are generated using the dev branch of Stanza as of 12/31/2023 and manually edited.

# Credits

- Brett Reynolds manually extracted numbered examples from manuscript files provided by Geoffrey Pullum
- Nathan Schneider implemented the page alignment code
- Tom Lupicki and Nathan Schneider implemented the conversion to YAML along with manual cleanup of the `.docx` files
- Tom Lupicki implemented the conversion to CoNLL-U (so far just for Ch. 1-2)

Citation for CGEL:

TODO

Citation for this dataset of CGEL examples:

TODO

For the related project on CGEL-style trees, see the [parent directory](../README.md).
