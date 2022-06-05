CGEL gold trees from Twitter with corresponding UD trees (silver from Stanza then manually corrected by Nathan Schneider)


## sentences.txt

These were taken from Brett's LaTeX trees with light editing for capitalization and punctuation. Removed gaps. Removed a couple of duplicate sentences, ungrammatical examples, and some stray LaTeX. Note that Brett's sentences were sometimes edited from an original attestation.

## sentences_fixed.conllu

This contains trees edited from parser output (ud_silver.conllu).

- [ ] TODO: finalize sentence IDs, add `sent_id` and `text` metadata lines

The [UD Annotatrix](https://github.com/jonorthwash/ud-annotatrix/) tool was used for editing.

In a very small number of cases (just 2 or 3) I had to edit the tokenization in Annotatrix. Sentence #31 was missing a final word ("fall"). Some punctuation was undersegmented, and in one case "its" was oversegmented.

I checked the UPOS and deprels. In some cases when fixing UPOS I fixed corresponding XPOS and features but I can't promise I did that systematically. The UPOS tagging seemed pretty accurate, though. I also added multiword tokens for clitics.

“Have a happier new year” and “May you have a happier new year” are both in here. maybe remove the first one?

Overall the biggest issues with the automatic parses seemed to be: scope of coordination; tricky relative clauses; and some copula constructions/BE as copula vs. aux.

### Noteworthy cases

s2 is TODO—do not trust that tree.

s35: many a __, s60: such a __: DET or ADJ? det:predet or amod? “such a” is consistently DET/det:predet in EWT, “many a” only occurs once

s39 What a remarkable claim to make: infinitival relative clause? Main clause is exclamative. 
UD policy doesn't currently support infinitival relatives.

s45: not sure about “big enough to…”

s57: “considering” is tricky—this is the subjectless semi-grammaticalized usage. 
Currently in EWT and GUM, in sentences like “Considering our options, we should do this” or 
“Considering that we have limited options, we should do this” it is treated as VERB/advcl. 
CGEL treats it as a preposition (pp. 971, 982-983). 
I added a note in the [UD issue on deverbal connectives](https://github.com/UniversalDependencies/UD_English-EWT/issues/179).
In the data noted it as TODO for now.


### Clause types

I went through and annotated clause type information in the UD MISC column. On the UD predicate, treating auxiliaries as modifiers. So mapping this onto CGEL trees will involve following Head relations with special rules for auxiliaries.

- finite clauses: `ClauseFinite=Yes`
- all clauses: `ClauseLevel=Main|Sub`
- all clauses: `ClauseType=Decl|OpenInt|ClosedInt|Excl|Imp|Other|Content,Decl|Content,OpenInt|Content,ClosedInt|Content,OpenInt,ClosedInt|Content,Excl|Compar|Rel|Inf|Inf,Rel|Part`
   * `Frag` can combine with these. E.g. `Frag,Decl` for a declarative main clause with omitted subject
- existential clauses: `Exist=Yes`

Nested clauses: because an entire clause can serve as a predicate in a copular clause, sometimes multiple clauses are headed by the same token (under [new UD guidelines](https://universaldependencies.org/changes.html#multiple-subjects)). So the same word gets multiple groups of clause features: the regular ones for the innermost clause, `ClauseFinite2`/`ClauseLevel2`/`ClauseType2` for the one containing that, etc. See s3 below.

#### Noteworthy cases

s3 [True narcissism is [just telling everyone your ideolect is a language]].  
`ClauseLevel=Sub|ClauseType=Part|ClauseFinite2=Yes|ClauseLevel2=Main|ClauseType2=Decl`

s29 One can never tell [when or even whether Alan was wholly serious].  
`ClauseType=Content,OpenInt,ClosedInt`

s32 [Kinda want to take my huge IKEA...lid and go sledding].  
`ClauseFinite=Yes|ClauseLevel=Main|ClauseType=Decl,Frag`

s44 May you have a happier new year!  
`ClauseFinite=Yes|ClauseLevel=Main|ClauseType=Other`

s46 Every New Yorker will receive and be prohibited from [giving away a horse].  
(treating "receive" + "be prohibited" as VP coordination, so no clause features on "prohibited")

#### Statistics

```
$ fgrep 'Clause' sentences_fixed.conllu | cut -f8 | sort | uniq -c
      8 acl
     19 acl:relcl
     20 advcl
     16 ccomp
      7 conj
      6 csubj
      1 discourse
      4 parataxis
     60 root
     12 xcomp
$ fgrep 'Clause' sentences_fixed.conllu | cut -f4 | sort | uniq -c
     18 ADJ
      1 ADV
      1 AUX
      1 DET
     17 NOUN
      4 PRON
      2 PROPN
    109 VERB
$ fgrep 'Clause' sentences_fixed.conllu | cut -f10 | cut -d'|' -f3- | sort | uniq -c
      4 ClauseFinite=Yes|ClauseLevel=Main|ClauseType=ClosedInt
      1 ClauseFinite=Yes|ClauseLevel=Main|ClauseType=ClosedInt|ClauseFinite2=Yes|ClauseLevel2=Main|ClauseType2=Decl
     48 ClauseFinite=Yes|ClauseLevel=Main|ClauseType=Decl
      7 ClauseFinite=Yes|ClauseLevel=Main|ClauseType=Decl,Frag
      1 ClauseFinite=Yes|ClauseLevel=Main|ClauseType=Decl|Exist=Yes
      1 ClauseFinite=Yes|ClauseLevel=Main|ClauseType=Excl
      4 ClauseFinite=Yes|ClauseLevel=Main|ClauseType=Imp
      2 ClauseFinite=Yes|ClauseLevel=Main|ClauseType=OpenInt
      1 ClauseFinite=Yes|ClauseLevel=Main|ClauseType=OpenInt|Exist=Yes
      1 ClauseFinite=Yes|ClauseLevel=Main|ClauseType=Other
      1 ClauseFinite=Yes|ClauseLevel=Sub|ClauseType=Compar
      1 ClauseFinite=Yes|ClauseLevel=Sub|ClauseType=Content,ClosedInt
     21 ClauseFinite=Yes|ClauseLevel=Sub|ClauseType=Content,Decl
      1 ClauseFinite=Yes|ClauseLevel=Sub|ClauseType=Content,Decl|Exist=Yes
      1 ClauseFinite=Yes|ClauseLevel=Sub|ClauseType=Content,Decl|Exist=Yes|ClauseFinite2=Yes|ClauseLevel2=Main|ClauseType2=Decl
      1 ClauseFinite=Yes|ClauseLevel=Sub|ClauseType=Content,Excl
      2 ClauseFinite=Yes|ClauseLevel=Sub|ClauseType=Content,OpenInt
      1 ClauseFinite=Yes|ClauseLevel=Sub|ClauseType=Content,OpenInt,ClosedInt
     18 ClauseFinite=Yes|ClauseLevel=Sub|ClauseType=Rel
     19 ClauseLevel=Sub|ClauseType=Inf
      3 ClauseLevel=Sub|ClauseType=Inf,Rel
     13 ClauseLevel=Sub|ClauseType=Part
      1 ClauseLevel=Sub|ClauseType=Part|ClauseFinite2=Yes|ClauseLevel2=Main|ClauseType2=Decl
```
