#!/bin/bash
# Quick debug script - run this to check auto-print status
# Usage: cd /home/erpnext/frappe-bench && ./apps/hospitality_core/hospitality_core/check_autoprint.sh

cd /home/erpnext/frappe-bench

echo "======================================"
echo "AUTO-PRINT DEBUG CHECK"
echo "======================================"

echo ""
echo "Running debug script..."
bench execute hospitality_core.hospitality_core.debug_autoprint.check_autoprint

echo ""
echo "======================================"
echo "If bench command not found, run:"
echo "  source env/bin/activate"
echo "  bench execute hospitality_core.hospitality_core.debug_autoprint.check_autoprint"
echo "======================================"
