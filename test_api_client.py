"""
Test UniHybrid API với Python requests
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("=" * 80)
    print("TEST 1: Health Check")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_root():
    """Test root endpoint."""
    print("=" * 80)
    print("TEST 2: Root Endpoint")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_execution_plan():
    """Test execution plan endpoint."""
    print("=" * 80)
    print("TEST 3: Execution Plan - Medium Scenario")
    print("=" * 80)
    
    params = {
        "chain_id": 8453,
        "token_in": "0x4200000000000000000000000000000000000006",  # WETH
        "token_out": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",  # USDC
        "amount_in": "1000000000000000000",  # 1 ETH
        "receiver": "0x1234567890abcdef1234567890abcdef12345678",
        "max_slippage_bps": 100,
        "performance_fee_bps": 3000,
        "max_matches": 8,
        "ob_min_improve_bps": 5,
        "me_slippage_limit": 200,
        "scenario": "medium"
    }
    
    print(f"Request params:")
    print(f"  Token In:  WETH ({params['token_in']})")
    print(f"  Token Out: USDC ({params['token_out']})")
    print(f"  Amount:    1 ETH")
    print(f"  Scenario:  {params['scenario']}")
    print()
    
    response = requests.get(f"{BASE_URL}/api/unihybrid/execution-plan", params=params)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        # Print key fields
        print("\n✅ SUCCESS - Execution Plan:")
        print("-" * 80)
        
        # Split
        split = data.get("split", {})
        print(f"\n📊 SPLIT:")
        print(f"   Total Input:      {int(split['amount_in_total']) / 10**18:.4f} ETH")
        print(f"   → Orderbook:      {int(split['amount_in_on_orderbook']) / 10**18:.4f} ETH ({int(split['amount_in_on_orderbook']) * 100 // int(split['amount_in_total'])}%)")
        print(f"   → AMM:            {int(split['amount_in_on_amm']) / 10**18:.4f} ETH ({int(split['amount_in_on_amm']) * 100 // int(split['amount_in_total'])}%)")
        
        # Savings
        print(f"\n💰 SAVINGS:")
        amm_ref = int(data['amm_reference_out']) / 10**6
        total_out = int(data['expected_total_out']) / 10**6
        sav_before = int(data['savings_before_fee']) / 10**6
        sav_after = int(data['savings_after_fee']) / 10**6
        
        print(f"   AMM Baseline:     {amm_ref:.2f} USDC")
        print(f"   Expected Total:   {total_out:.2f} USDC")
        print(f"   Savings Before:   {sav_before:.2f} USDC")
        print(f"   Savings After:    {sav_after:.2f} USDC")
        print(f"   Performance Fee:  {int(data['performance_fee_amount']) / 10**6:.2f} USDC")
        
        # Hook data
        print(f"\n📦 HOOK DATA:")
        hook_args = data['hook_data_args']
        print(f"   tokenIn:              {hook_args['tokenIn']}")
        print(f"   tokenOut:             {hook_args['tokenOut']}")
        print(f"   amountInOnOrderbook:  {hook_args['amountInOnOrderbook']}")
        print(f"   maxMatches:           {hook_args['maxMatches']}")
        print(f"   slippageLimit:        {hook_args['slippageLimit']}")
        print(f"   Encoded:              {data['hook_data'][:66]}...")
        
        # Metadata
        if 'metadata' in data:
            meta = data['metadata']
            print(f"\n📋 METADATA:")
            print(f"   Pool:     {meta['pool_address']}")
            print(f"   Scenario: {meta['scenario']}")
            print(f"   Symbols:  {meta['token_in_symbol']} → {meta['token_out_symbol']}")
        
        print()
        
    else:
        print(f"\n❌ ERROR:")
        print(json.dumps(response.json(), indent=2))
        print()

if __name__ == "__main__":
    import time
    
    print("\n" + "=" * 80)
    print("UniHybrid API Test Suite")
    print("=" * 80 + "\n")
    
    # Wait for server
    print("Waiting for server to be ready...")
    time.sleep(2)
    
    try:
        test_health()
        test_root()
        test_execution_plan()
        
        print("=" * 80)
        print("✅ ALL TESTS COMPLETED!")
        print("=" * 80)
        
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to API server")
        print("Make sure the server is running: uvicorn api.main:app --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"❌ ERROR: {e}")
