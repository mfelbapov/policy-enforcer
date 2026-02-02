
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server import check_approval_threshold, get_employee_info, CheckApprovalInput, GetEmployeeInput

async def verify():
    print("Verifying Employee Loading...")
    # Test existing employee
    emp_input = GetEmployeeInput(employee_id="emp001")
    result = await get_employee_info(emp_input)
    print(f"Result for emp001: {result[:100]}...")
    
    if "Alice Chen" in result:
        print("✅ Employee loaded correctly")
    else:
        print("❌ Employee not loaded correctly")
        
    print("\nVerifying Rules Loading...")
    # Test threshold (previously hardcoded < 500)
    # Check $100 (Direct Manager)
    approval_input = CheckApprovalInput(
        employee_id="emp001",
        amount=100.0,
        expense_type="Travel"
    )
    result_json = await check_approval_threshold(approval_input)
    result = json.loads(result_json)
    
    req = result.get("approval_requirements", {})
    print(f"Amount: $100, Required: {req.get('required_approver_level')}")
    
    if req.get("required_approver_level") == "Direct Manager":
        print("✅ Low amount threshold correct")
    else:
        print(f"❌ Low amount threshold incorrect: {req}")

    # Test threshold (previously hardcoded < 2000)
    # Check $1500 (Department Head)
    approval_input = CheckApprovalInput(
        employee_id="emp001",
        amount=1500.0,
        expense_type="Travel"
    )
    result_json = await check_approval_threshold(approval_input)
    result = json.loads(result_json)
    
    req = result.get("approval_requirements", {})
    print(f"Amount: $1500, Required: {req.get('required_approver_level')}")
    
    if req.get("required_approver_level") == "Department Head":
        print("✅ Medium amount threshold correct")
    else:
        print(f"❌ Medium amount threshold incorrect: {req}")

if __name__ == "__main__":
    asyncio.run(verify())
