#!/bin/bash
# Quick capture for Phase 2 configurations only
# Captures: QoS, VPN, and Mobile Agent configs

echo "=========================================="
echo "Quick Capture - Phase 2 Only"
echo "=========================================="
echo
echo "Capturing Phase 2 configurations:"
echo "  - qos_profile"
echo "  - qos_policy_rule"
echo "  - ike_crypto_profile"
echo "  - ipsec_crypto_profile"
echo "  - ike_gateway"
echo "  - ipsec_tunnel"
echo "  - agent_profile"
echo
echo "Use this if you already captured Phase 1."
echo "This will take ~1-2 minutes!"
echo
echo "Starting capture..."
echo

cd /home/lindsay/Code/pa_config_lab

python scripts/capture_production_examples.py \
  --tenant "SCM Lab" \
  --types \
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
