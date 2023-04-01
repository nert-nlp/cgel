Interannotator Agreement Data
=============================

Following the development of the initial data (ewt.cgel and twitter.cgel), full annotation guidelines, validation code, and web annotation tool for CGEL trees, an interannotator agreement study was conducted between the two original annotators on new data (from the UD_English-EWT test set).

First, 5 sentences were randomly sampled as pilot sentences (`pilot5`). The two annotators made trees for these sentences to familiarize themselves with the web tool workflow. Upon comparing the two sets of trees and adjudicating differences, annotation policies raised by the sentences were discussed.

Then, 50 new sentences were sampled (`iaa50`) for the actual IAA experiment. The two annotators worked on these independently in the web tool, first with the detailed CGEL-specific validation rules turned off. These are the `.novalidator` files. Then the validation messages were turned on and annotators revised their own trees (`.validator` files). Finally, there was a cooperative adjudication step of comparing the two `.validator` files in a text editor and resolving disagreements. Many of these were minor errors or borderline decisions, but some substantive issues were surfaced that triggered new policies (e.g. regarding dollar signs occurring before the amount). The `.adjudicated` file is the result of this process, which took about 4 hours of joint work for the 50 sentences.

Finally, UD sentence IDs, text strings, punctuation, and lemmas were incorporated to produce the release versions of the data in the `datasets` directory.

Details
-------

**Sentence sampling procedure:** This used `sample_ud_sents.py`. The sentences were selected randomly subject to two constraints: (i) a minimum of 5 UD words (including punctuation), and (ii) no `goeswith` dependencies which indicate overtokenization in the spelling.

**Preprocessing:** The `udptb2cgelpos.py` script was used to generate a file with tagged versions of the sentences for import into the annotation tool. This relies mostly on UD POS tags, but also references the PTB-style trees to infer some gaps (mainly corresponding to WH-traces). Annotators corrected the heuristic CGEL POS tags and added new gaps as well (mostly for noncanonical phrase ordering). Annotators were allowed to edit the tokenization and spelling, e.g. inserting hyphens to turn two UD nodes into a single CGEL lexeme with a single POS. Annotators worked independently on these tag files before making trees (in some cases going back to revise, as the web application does support direct changes to tokens).

**Annotation tool grammar:** The annotation tool relies on the activedop parser to suggest possible trees as preannotation. Annotators used the same grammar, trained on (3 training files?), to initialize this parser. Preannotations benefit from the POS tags, which are easy to (semi)automatically specify, hence the preprocessing step. The parser training and execution used default settings (except that the limit on the number of training trees was increased to consider all training trees). The active annotation setup in the web tool means that saving a tree can extend the grammar and open up additional potential parses for other sentences in the batch.
