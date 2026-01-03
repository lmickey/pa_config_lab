#!/bin/bash
# Quick capture for newly added configurations
# Run this instead of full capture to save time!

echo "=========================================="
echo "Quick Capture - New Configurations Only"
echo "=========================================="
echo
echo "Capturing:"
echo "  - schedule (new)"
echo "  - service_group (new)"
echo "  - antivirus_profile (updated)"
echo "  - wildfire_profile (updated)"
echo
echo "This will take ~1-2 minutes instead of 20 minutes!"
echo
echo "Starting capture..."
echo

cd /home/lindsay/Code/pa_config_lab

python scripts/capture_production_examples.py \
  --tenant "SCM Lab" \
  --types schedule service_group antivirus_profile wildfire_profile

echo
echo "=========================================="
echo "Done! Check the output above for results."
echo "=========================================="
