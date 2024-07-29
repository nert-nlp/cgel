# CGELBank Statistics

Analyzing 29 files:

- [datasets/twitter.cgel](datasets/twitter.cgel)
- [datasets/ewt.cgel](datasets/ewt.cgel)
- [datasets/ewt-test_pilot5.cgel](datasets/ewt-test_pilot5.cgel)
- [datasets/ewt-test_iaa50.cgel](datasets/ewt-test_iaa50.cgel)
- [datasets/trial/ewt-trial.cgel](datasets/trial/ewt-trial.cgel)
- [datasets/trial/twitter-etc-trial.cgel](datasets/trial/twitter-etc-trial.cgel)
- [datasets/oneoff/whatcolorsocks.cgel](datasets/oneoff/whatcolorsocks.cgel)
- [datasets/oneoff/insectspecies.cgel](datasets/oneoff/insectspecies.cgel)
- [datasets/oneoff/howstupid.cgel](datasets/oneoff/howstupid.cgel)
- [datasets/oneoff/oakland.cgel](datasets/oneoff/oakland.cgel)
- [datasets/oneoff/dinner.cgel](datasets/oneoff/dinner.cgel)
- [datasets/oneoff/bakhmut.cgel](datasets/oneoff/bakhmut.cgel)
- [datasets/oneoff/abortion.cgel](datasets/oneoff/abortion.cgel)
- [datasets/oneoff/bullying.cgel](datasets/oneoff/bullying.cgel)
- [datasets/oneoff/howcommon.cgel](datasets/oneoff/howcommon.cgel)
- [datasets/oneoff/lookaround.cgel](datasets/oneoff/lookaround.cgel)
- [datasets/oneoff/xkcd-garden-path.cgel](datasets/oneoff/xkcd-garden-path.cgel)
- [datasets/oneoff/usc-rule2002a.cgel](datasets/oneoff/usc-rule2002a.cgel)
- [datasets/oneoff/bedtime.cgel](datasets/oneoff/bedtime.cgel)
- [datasets/oneoff/mutantfleas.cgel](datasets/oneoff/mutantfleas.cgel)
- [datasets/oneoff/vichy.cgel](datasets/oneoff/vichy.cgel)
- [datasets/oneoff/usc34-1.cgel](datasets/oneoff/usc34-1.cgel)
- [datasets/oneoff/handup.cgel](datasets/oneoff/handup.cgel)
- [datasets/oneoff/ranger.cgel](datasets/oneoff/ranger.cgel)
- [datasets/oneoff/schumer.cgel](datasets/oneoff/schumer.cgel)
- [datasets/oneoff/leisure.cgel](datasets/oneoff/leisure.cgel)
- [datasets/oneoff/authority.cgel](datasets/oneoff/authority.cgel)
- [datasets/oneoff/bethebest.cgel](datasets/oneoff/bethebest.cgel)
- [datasets/oneoff/swingingbed.cgel](datasets/oneoff/swingingbed.cgel)

## Overview

- Trees: 280
- Nodes: 13202
- Lexical Nodes: 4782 (17.1/tree)
- Lexical Insertions (nodes where surface string is empty due to typo): 5
- Gaps: 195
- Punctuation Tokens: 494
- Avg Tree Depth: 12.3


## POS categories

| POS         |   count |
|:------------|--------:|
| N           |    1238 |
| P           |     630 |
| V           |     615 |
| D           |     541 |
| N_pro       |     463 |
| V_aux       |     395 |
| Adj         |     310 |
| Adv         |     236 |
| Coordinator |     176 |
| Sdr         |     170 |
| Int         |       8 |

## Lemmas occurring >=5 times, by categories the lemma appears in

- `{D}`: a all another any enough no some the this two
- `{V, V_aux}`: be do have
- `{P}`: about after at because by from here in now of on out over than then through up when with
- `{D, Sdr}`: that
- `{N}`: $ Bush company day food horse money people place point time year
- `{N_pro}`: he it she they we who you
- `{V_aux}`: can could may should will would
- `{V}`: come find get give go know make need require say see take tell think use want
- `{Adv}`: also even how just not only really why
- `{N, V}`: call charge file help issue look start try work
- `{Adj, D, N_pro}`: what
- `{N_pro, P}`: there
- `{P, Sdr}`: for if to
- `{N, N_pro}`: I
- `{Adj, Adv}`: very
- `{Adj}`: different first good great new
- `{Coordinator}`: / and but or
- `{Adj, Adv, Int}`: well
- `{Adv, Coordinator, Int, P}`: so
- `{Adv, D}`: more most
- `{D, N, N_pro}`: one
- `{Adj, V}`: own
- `{Adv, N, V}`: right
- `{Adj, P, V}`: like
- `{Adv, P}`: as
- `{D, N_pro}`: which
- `{N, P}`: back
- `{Adj, N, V}`: deal

## All lexemes of closed-class categories

- `D`: 1, 10, 11, 11,000, 11780, 12, 120, 14000, 15, 1584, 16, 2, 2.3, 20, 200, 200000, 20000000, 2017, 21, 22, 24, 28, 3.7, 30, 300, 4, 45, 5, 500, 53, 600, 90, a, a few, a little, all, an, another, any, anybody, anyone, anything, anywhere, billion, both, each, enough, every, everybody, everyone, everything, fourteen, hundred, least, many, many a, million, more, most, much, no, no one, none, once, one, several, some, someone, something, sometimes, somewhere, that, the, this, those, three, two, what, which
- `N_pro`: I, he, him, his, it, its, my, one, our, she, their, them, there, they, tomorrow, we, what, which, who, whom, yesterday, you, you all
- `V_aux`: be, can, cannot, could, do, have, may, might, must, should, will, would
- `P`: @, Like, a.m., about, above, according, after, against, along, around, as, aside, at, away, back, because, before, behind, below, between, by, considering, coupled, despite, down, due, during, except, for, forward, from, here, if, in, in order, including, inside, into, irrespective, like, near, next, now, of, off, on, onboard, once, out, outside, over, past, per, plus, regarding, since, so, so long as, than, then, there, through, throughout, to, toward, towards, under, until, up, upon, upstairs, when, where, while, with, within, without
- `Sdr`: for, if, that, to, whether
- `Coordinator`: &, -, /, and, but, etc, or, plus, so, v

## Nonterminal categories

| category     |   count |
|:-------------|--------:|
| Nom          |    1949 |
| NP           |    1593 |
| VP           |    1388 |
| Clause       |    1066 |
| PP           |     645 |
| DP           |     539 |
| AdjP         |     352 |
| AdvP         |     242 |
| GAP          |     195 |
| Clause_rel   |     180 |
| Coordination |     178 |
| N@flat       |      52 |
| NP+PP        |       9 |
| PP_strand    |       8 |
| IntP         |       8 |
| NP+Clause    |       5 |
| D@flat       |       4 |
| NP+AdvP      |       3 |
| AdjP+PP      |       3 |
| NP+AdjP      |       1 |

## Functions

| function          |   count |
|:------------------|--------:|
| Head              |    7870 |
| Mod               |    1082 |
| Comp              |     747 |
| Obj               |     719 |
| Det               |     532 |
| Subj              |     516 |
| Coordinate        |     361 |
| Marker            |     345 |
| (root)            |     280 |
| PredComp          |     168 |
| Supplement        |     150 |
| Flat              |     117 |
| Prenucleus        |      92 |
| Det-Head          |      86 |
| Postnucleus       |      22 |
| Head-Prenucleus   |      16 |
| Particle          |      14 |
| DisplacedSubj     |      14 |
| Comp_ind          |      13 |
| Obj_dir           |      12 |
| Obj_ind           |      12 |
| ExtraposedSubj    |      10 |
| Mod-Head          |       8 |
| Vocative          |       4 |
| Compounding       |       4 |
| Obj+Mod           |       4 |
| Marker-Head       |       2 |
| Obj+PredComp/Comp |       1 |
| ExtraposedObj     |       1 |
