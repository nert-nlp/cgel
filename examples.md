Rough notes for CGEL annotation, to be eventually made into guidelines.

# Projection

- N → Nom → NP → Clause
- Adj → AdjP
- V → VP → Clause
- D → DP → NP
- P → PP
- Adv → AdvP

# advmod

> **very interesting**
```
(AdjP
    :Mod (AdvP
        :Head (Adv :t "very"))
    :Head (Adj :t "interesting"))
```

> **Why do you think they are mean?**
```
(Clause
    :Prenucleus (AdvP
        :Head (Adv :t "why"))
    :Head (Clause
        :Prenucleus (VP
            :Head (V :t "do"))
        :Head (Clause
            :Subj (NP
                :Head (Nom
                    :Head (N :t "you")))
            :Head (VP
                :Head (V :t "think")
                :Comp (Clause
                    :Head (Clause
                        :Subj (NP
                            :Head (Nom
                                :Head (N :t "they")))
                        :Head (VP
                            :Head (V :t "are")
                            :PredComp (AdjP
                                :Head (Adj :t "mean")))))))))
```

# aux

auxiliary verbs, these are heads in CGEL

> **I am writing**
```
(Clause
    :Subj (NP
        :Head (Nom
            :Head (N :t "I")))
    :Head (VP
        :Head (V :t "am")
        :Comp (Clause
            :Head (VP
                :Head (V :t "writing")))))
```

> **am I writing?**

# acl

relative clauses modifying nouns

> **a chance for the suckups to suck**
```
(NP
    :Det (DP
        :Head (D :t "a"))
    :Head (Nom
        :Head (x / N :t "chance")
        :Mod (Clause_rel
            :Marker (Subrd :t "for")
            :Head (Clause
                :Subj (NP
                    :Det (DP
                        :Head (D :t "the"))
                    :Head (Nom
                        :Head (N :t "suckups")))
                :Head (VP
                    :Marker (Subdr :t "to")
                    :Head (VP
                        :Head (V :t "suck")
                        :Mod x))))))
```

> **a chance to present the story**

```
(NP
    :Det (DP
        :Head (D :t "a"))
    :Head (Nom
        :Head(x / N :t "chance")
        :Mod (Clause_rel
            :Head (VP
                :Marker (Subdr :t "to")
                :Head (VP
                    :Head (V :t "present")
                    :Obj (NP
                        :Det (DP
                            :Head (D :t "the"))
                        :Head (Nom
                            :Head (N :t "story")))
                    :Mod x)))))
```

> **the right to be the Santa of nuclear weapons**

```
(NP
    :Det (DP
        :Head (D :t "the"))
    :Head (Nom
        :Head (x / N :t "right")
        :Mod (Clause_rel
            :Head (VP
                :Marker (Subdr :t "to"))
                :Head (VP
                    :Head (V :t "be")
                    :PredComp (NP
                        :Det (DP
                            :Head (D :t "the"))
                        :Head (Nom
                            :Head (N :t "Santa")
                            :Comp (PP
                                :Head (P :t "of")
                                :Obj (NP
                                    :Head (Nom
                                        :Mod (AdjP
                                            :Head (Adj :t "nuclear"))
                                        :Head (N :t "weapons"))))))
                    :Mod x))))
```

## acl:relcl

> **what Liz bought**
```
(Clause
    :Prenucleus (x / NP
        :Head (Nom
            :Head (N :t "what")))
    :Nucleus (Clause
        :Subj (NP
            :Head (Nom
                :Head (N :t "Liz")))
        :Head (VP
            :Head (V :t "bought")
            :Obj x)))
```

> **what Max said Liz bought**
```
(Clause
    :Prenucleus (x / NP
        :Head (Nom
            :Head (N :t "what")))
    :Nucleus (Clause
        :Subj (NP
            :Head (Nom
                :Head (N :t "Max")))
        :Head (VP
            :Head (V "said")
            :Comp (Clause
                :Subj (NP
                    :Head (Nom
                        :Head (N :t "Liz")))
                :Head (VP
                    :Head (V :t "bought")
                    :Obj x)))))
```


# det

determiners

> **the kid**
```
(NP
    :Det (DP
        :Head (D :t "the"))
    :Head (Nom
        :Head (N :t "kid")))
```