#!/bin/bash

REM_DUP_LINES_DIR="data/counters/*"
TMP_FILE="tmp_sorted.txt"

for file in $REM_DUP_LINES_DIR
do
    before=$(wc -l "$file" | awk -F' ' '{print $1}')
    sort "$file" | uniq > "$TMP_FILE"
    after=$(wc -l "$TMP_FILE" | awk -F' ' '{print $1}')
    if [ $before -ne $after ]; then
        echo "Before $before"
        echo "After $after"
        echo "Do overwrite for $file"
        mv $TMP_FILE $file
    fi
done
