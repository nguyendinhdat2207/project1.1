#!/bin/bash
#
# Test UniHybrid API Endpoint
#

echo "=========================================="
echo "TEST: UniHybrid API Execution Plan"
echo "=========================================="
echo ""

# Base mainnet addresses
WETH="0x4200000000000000000000000000000000000006"
USDC="0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
RECEIVER="0x1234567890abcdef1234567890abcdef12345678"
AMOUNT_IN="1000000000000000000"  # 1 ETH

echo "Test 1: Health Check"
echo "----------------------------------------"
curl -s "http://localhost:8000/health" | python3 -m json.tool
echo ""
echo ""

echo "Test 2: Root Endpoint"
echo "----------------------------------------"
curl -s "http://localhost:8000/" | python3 -m json.tool
echo ""
echo ""

echo "Test 3: Execution Plan - Medium Scenario"
echo "----------------------------------------"
echo "Request:"
echo "  Token In:  WETH ($WETH)"
echo "  Token Out: USDC ($USDC)"
echo "  Amount:    1 ETH"
echo "  Scenario:  medium"
echo ""

curl -s "http://localhost:8000/api/unihybrid/execution-plan?\
chain_id=8453&\
token_in=$WETH&\
token_out=$USDC&\
amount_in=$AMOUNT_IN&\
receiver=$RECEIVER&\
max_slippage_bps=100&\
performance_fee_bps=3000&\
max_matches=8&\
ob_min_improve_bps=5&\
me_slippage_limit=200&\
scenario=medium" | python3 -m json.tool

echo ""
echo ""
echo "=========================================="
echo "✅ API Tests Completed!"
echo "=========================================="
