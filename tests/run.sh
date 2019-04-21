#!/bin/sh

echo "running converter tests"

total=0
passed=0
for f in *.musicxml *.mxl; do
  reflog=`echo "$f" | sed 's/\.[^.]*//'`.txt
  ../converter.py "$f" > tmp.$$.txt
  diff $reflog tmp.$$.txt && passed=`expr $passed + 1` || echo "error: reflog doesn't match for $f"
  total=`expr $total + 1`
done

rm tmp.*.txt

echo "$total run, $passed passed"
