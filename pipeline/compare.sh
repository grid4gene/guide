#!/bin/bash

sort -u <(grep -v '^#' $1 | cut -f1,2,4,5) > a
sort -u <(grep -v '^#' $2 | cut -f1,2,4,5) > b
comm -23 a b > a_only
comm -13 a b > b_only
comm -12 a b > ab

numer=`cat a_only b_only | wc -l`
denom=`cat ab a_only b_only | wc -l`
dist=`echo "$numer/$denom" | bc -l`
sim=`echo "(1-$dist)*100" | bc -l`

echo $sim

