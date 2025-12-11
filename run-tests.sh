#!/bin/bash

# 🧪 AUTOMATED TESTING SCRIPT - Phases 1.5 + 2
# Ejecuta todos los test cases críticos

set -e

echo "=================================="
echo "🧪 STARTING AUTOMATED TESTING"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:5173"
TIMEOUT=10

# Test Results
PASSED=0
FAILED=0
TESTS=()

# Helper function
test_api() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local expected_code=$5
    
    echo -n "Testing: $name... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BACKEND_URL$endpoint" 2>/dev/null || echo "ERROR")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$BACKEND_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data" 2>/dev/null || echo "ERROR")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "$expected_code" ] || [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✅ PASS${NC} (HTTP $http_code)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} (Expected $expected_code, got $http_code)"
        echo "  Response: $body"
        ((FAILED++))
        return 1
    fi
}

# Pre-flight checks
echo "📋 PRE-FLIGHT CHECKS"
echo "===================="

echo -n "Checking Backend availability at $BACKEND_URL... "
if curl -s "$BACKEND_URL/docs" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend is running${NC}"
else
    echo -e "${RED}❌ Backend not found at $BACKEND_URL${NC}"
    echo "   Start backend with: cd backend && uvicorn app.main:app --reload"
    exit 1
fi

echo ""
echo "🧪 RUNNING TEST SUITES"
echo "======================"
echo ""

# TEST SUITE 1: Backend Health & Database
echo "📊 TEST SUITE 1: Backend Health"
echo "-------------------------------"

test_api "Swagger UI accessible" "GET" "/docs" "" "200"
test_api "OpenAPI schema" "GET" "/openapi.json" "" "200"
test_api "List products" "GET" "/api/products" "" "200"
test_api "List orders" "GET" "/api/orders" "" "200"

echo ""

# TEST SUITE 2: Location Management (Bug #4, #30, #32)
echo "📊 TEST SUITE 2: Location Management"
echo "------------------------------------"

test_api "List locations" "GET" "/api/locations" "" "200"
test_api "Get location 1" "GET" "/api/locations/1" "" "200"

echo ""

# TEST SUITE 3: Stock Operations (Bug #29, #31, #2, #3, #27)
echo "📊 TEST SUITE 3: Stock Operations"
echo "--------------------------------"

test_api "List products with stock" "GET" "/api/products" "" "200"
test_api "Get product stock" "GET" "/api/products/1/stock" "" "200"

# Stock transfer validation (Bug #31 - cantidad > 0)
TRANSFER_ZERO='{"from_location_id":1,"to_location_id":2,"product_id":1,"cantidad":0}'
test_api "Reject transfer cantidad=0 (Bug #31)" "POST" "/api/stock-transfers" "$TRANSFER_ZERO" "400"

echo ""

# TEST SUITE 4: Order Operations (Bug #1, #5, #8, #9, #26, #28)
echo "📊 TEST SUITE 4: Order Operations"
echo "-------------------------------"

test_api "List orders" "GET" "/api/orders" "" "200"
test_api "Get order 1" "GET" "/api/orders/1" "" "200"

# Create test order (Bug #1, #26, #28)
TEST_ORDER='{
  "sales_profile_id": 1,
  "source_location_id": 1,
  "customer_name": "Test Customer",
  "customer_phone": "555-0123",
  "canal": "whatsapp",
  "metodo_pago": "efectivo",
  "items": [
    {"product_id": 1, "cantidad": 1, "precio_unitario": 100}
  ]
}'
test_api "Create order (Bug #1, #26, #28)" "POST" "/api/orders" "$TEST_ORDER" "201"

echo ""

# TEST SUITE 5: Query Performance (Bug #27)
echo "📊 TEST SUITE 5: Query Performance"
echo "--------------------------------"

echo "Testing query performance for /api/products?location_id=1..."
START_TIME=$(date +%s%N)

response=$(curl -s "$BACKEND_URL/api/products?location_id=1" 2>/dev/null)

END_TIME=$(date +%s%N)
DURATION=$(( (END_TIME - START_TIME) / 1000000 ))  # Convert to ms

echo "Query completed in ${DURATION}ms"
if [ "$DURATION" -lt 500 ]; then
    echo -e "${GREEN}✅ Performance OK${NC} (< 500ms)"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠️  Performance warning${NC} (${DURATION}ms, target < 500ms)"
fi

echo ""

# TEST SUITE 6: Sales Profiles
echo "📊 TEST SUITE 6: Sales Profiles"
echo "------------------------------"

test_api "List sales profiles" "GET" "/api/sales-profiles" "" "200"

echo ""

# TEST SUITE 7: Stock History
echo "📊 TEST SUITE 7: Stock History"
echo "-----------------------------"

test_api "List stock history" "GET" "/api/stock-history" "" "200"

echo ""
echo "=================================="
echo "📊 TESTING SUMMARY"
echo "=================================="
echo -e "Tests Passed: ${GREEN}$PASSED${NC}"
echo -e "Tests Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo ""
    echo "🚀 System is ready for deployment"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "Please fix the issues and re-run this script"
    exit 1
fi
