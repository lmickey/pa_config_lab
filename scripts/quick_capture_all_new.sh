#!/bin/bash
# Quick capture for ALL newly added configurations
# Captures: schedules, service groups, security profiles, QoS, VPN, mobile agent

echo "=========================================="
echo "Quick Capture - All New Configurations"
echo "=========================================="
echo
echo "Capturing:"
echo "  Phase 1 (earlier):"
echo "    - schedule"
echo "    - service_group"
echo "    - antivirus_profile"
echo "    - wildfire_profile"
echo
echo "  Phase 2 (just added):"
echo "    - qos_profile"
echo "    - qos_policy_rule"
echo "    - ike_crypto_profile"
echo "    - ipsec_crypto_profile"
echo "    - ike_gateway"
echo "    - ipsec_tunnel"
echo "    - agent_profile"
echo
echo "This will take ~2-3 minutes instead of 20 minutes!"
echo
echo "Starting capture..."
echo

cd /home/lindsay/Code/pa_config_lab

python scripts/capture_production_examples.py \
  --tenant "SCM Lab" \
  --types \
    schedule \
    service_group \
    antivirus_profile \
    wildfire_profile \
    qos_profile \
    qos_policy_rule \
    ike_crypto_profile \
    ipsec_crypto_profile \
    ike_gateway \
    ipsec_tunnel \
    agent_profile

echo
echo "=========================================="
echo "Done! Check the output above for results."
echo "=========================================="
