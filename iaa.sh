#!/bin/bash

set -eux

A1PRE=datasets/iaa/ewt-test_iaa50.nschneid.novalidator.cgel
A2PRE=datasets/iaa/ewt-test_iaa50.brettrey.novalidator.cgel
A1=datasets/iaa/ewt-test_iaa50.nschneid.validator.cgel
A2=datasets/iaa/ewt-test_iaa50.brettrey.validator.cgel
ADJ=datasets/iaa/ewt-test_iaa50.adjudicated.cgel
OUT=datasets/iaa/iaa.out

echo "# A1PRE ~ A2PRE" > $OUT
echo "+python eval.py $A1PRE $A2PRE" >> $OUT
python eval.py $A1PRE $A2PRE >> $OUT

echo "" >> $OUT
echo "# A1PRE ~ A1" >> $OUT
echo "+python eval.py $A1PRE $A1" >> $OUT
python eval.py $A1PRE $A1 >> $OUT

echo "" >> $OUT
echo "# A2PRE ~ A2" >> $OUT
echo "+python eval.py $A2PRE $A2" >> $OUT
python eval.py $A2PRE $A2 >> $OUT

echo "" >> $OUT
echo "# A1 ~ A2" >> $OUT
echo "+python eval.py $A1 $A2" >> $OUT
python eval.py $A1 $A2 >> $OUT

echo "" >> $OUT
echo "# ADJ ~ A1PRE" >> $OUT
echo "+python eval.py $ADJ $A1PRE" >> $OUT
python eval.py $ADJ $A1PRE >> $OUT

echo "" >> $OUT
echo "# ADJ ~ A2PRE" >> $OUT
echo "+python eval.py $ADJ $A2PRE" >> $OUT
python eval.py $ADJ $A2PRE >> $OUT

echo "" >> $OUT
echo "# ADJ ~ A1" >> $OUT
echo "+python eval.py $ADJ $A1" >> $OUT
python eval.py $ADJ $A1 >> $OUT

echo "" >> $OUT
echo "# ADJ ~ A2" >> $OUT
echo "+python eval.py $ADJ $A2" >> $OUT
python eval.py $ADJ $A2 >> $OUT
