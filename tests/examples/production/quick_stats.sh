#!/bin/bash
# Quick statistics about captured production examples

echo "=========================================="
echo "Production Example Capture Statistics"
echo "=========================================="
echo

echo "Total JSON files: $(find raw -name "*.json" | wc -l)"
echo

echo "Files by type:"
for dir in raw/*/; do
    type_name=$(basename "$dir")
    count=$(ls "$dir" 2>/dev/null | wc -l)
    if [ $count -gt 0 ]; then
        printf "  %-30s %3d files\n" "$type_name:" "$count"
    fi
done | sort -t: -k2 -rn
echo

echo "Largest files:"
find raw -name "*.json" -exec ls -lh {} \; | sort -k5 -rh | head -5 | awk '{print "  " $9 " (" $5 ")"}'
echo

echo "Sample files:"
find raw -name "*.json" | head -3 | while read f; do
    echo "  - $f"
done
echo

echo "To explore a specific type:"
echo "  ls raw/<type>/"
echo "  cat raw/<type>/<file>.json | jq"
