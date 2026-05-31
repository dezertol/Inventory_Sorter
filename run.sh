#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 -m inventory_sorter scan /home/chansen/Pictures/Need_to_sort \
  --destination /run/user/1000/gvfs/smb-share:server=wdmycloudex4100.local,share=chansen/CleanUp \
  --apply \
  --remove-duplicates \
  --verbose
