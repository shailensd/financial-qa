"""
Quick test to verify CALCULATE tool now accepts context variables.
"""

import sys
sys.path.insert(0, '.')

from app.agent.tools import _execute_calculate

# Test 1: Simple literal expression (should work before and after fix)
print("Test 1: Literal expression")
try:
    result = _execute_calculate({"expression": "100 + 200"})
    print(f"✓ Result: {result}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: Variable without context (should fail)
print("\nTest 2: Variable without context")
try:
    result = _execute_calculate({"expression": "total_revenue"})
    print(f"✓ Result: {result}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 3: Variable with context (should work after fix)
print("\nTest 3: Variable with context")
try:
    context = {"total_revenue": 383285}
    result = _execute_calculate({"expression": "total_revenue"}, context)
    print(f"✓ Result: {result}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 4: Expression with context variables (should work after fix)
print("\nTest 4: Expression with context variables")
try:
    context = {"revenue_2023": 383285, "revenue_2022": 394328}
    result = _execute_calculate(
        {"expression": "(revenue_2023 - revenue_2022) / revenue_2022 * 100"},
        context
    )
    print(f"✓ Result: {result}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n✅ All tests completed!")
