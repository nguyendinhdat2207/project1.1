# API Tests

Tests cho FastAPI endpoint `/api/unihybrid/execution-plan`

## Files

### test_api_client.py
Python client test cho API endpoint.

**Usage:**
```bash
# Make sure API server is running
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Run test
python tests/api/test_api_client.py
```

**Tests:**
- Health check endpoint
- Root endpoint
- Execution plan endpoint (medium scenario)

**Output:**
- Validates all response fields
- Shows split, savings, hook data
- Compares with AMM baseline

### test_api.sh
Bash script để test API endpoints với curl.

**Usage:**
```bash
# Make sure API server is running
cd /home/dinhdat/Project1
./tests/api/test_api.sh
```

**Tests:**
- GET /health
- GET /
- GET /api/unihybrid/execution-plan

## Requirements

- API server must be running on port 8000
- Virtual environment activated
- All dependencies installed

## Expected Results

All tests should return:
- ✅ Health check: 200 OK
- ✅ Root endpoint: 200 OK  
- ✅ Execution plan: 200 OK with complete JSON response
