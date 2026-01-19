"""
MCP Server: Tool Definitions for Policy Enforcer

FDE-Level Concepts Demonstrated:
1. Proper tool naming (service_action_resource pattern)
2. Pydantic validation with Field constraints
3. Tool annotations (readOnlyHint, etc.)
4. Response format options (JSON vs Markdown)
5. Error handling with actionable messages
"""

from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from embeddings import search_policies
from config import RETRIEVAL_CONFIDENCE_THRESHOLD

# =============================================================================
# Server Initialization
# =============================================================================

# FDE Note: Server name follows convention: {service}_mcp
mcp = FastMCP("policy_enforcer_mcp")

# =============================================================================
# Mock Employee Database
# =============================================================================

# FDE Note: In production, this connects to your HRIS/AD/LDAP
# For demo, we use a mock database

EMPLOYEE_DATABASE = {
    "emp001": {
        "id": "emp001",
        "name": "Alice Chen",
        "email": "alice.chen@company.com",
        "level": 5,
        "title": "Senior Software Engineer",
        "department": "Engineering",
        "manager_id": "emp010",
    },
    "emp002": {
        "id": "emp002",
        "name": "Bob Martinez",
        "email": "bob.martinez@company.com",
        "level": 9,
        "title": "Director of Engineering",
        "department": "Engineering",
        "manager_id": "emp015",
    },
    "emp003": {
        "id": "emp003",
        "name": "Carol Williams",
        "email": "carol.williams@company.com",
        "level": 11,
        "title": "VP of Product",
        "department": "Product",
        "manager_id": "emp020",
    },
    "emp004": {
        "id": "emp004",
        "name": "David Kim",
        "email": "david.kim@company.com",
        "level": 3,
        "title": "Software Engineer",
        "department": "Engineering",
        "manager_id": "emp001",
    },
}

# =============================================================================
# Input Models (Pydantic v2)
# =============================================================================

class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class GetEmployeeInput(BaseModel):
    """Input model for employee lookup."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"  # Reject unknown fields
    )
    
    employee_id: str = Field(
        ...,
        description="Employee ID (e.g., 'emp001', 'emp002')",
        min_length=1,
        max_length=50,
        pattern=r"^emp\d{3}$"  # Enforce format
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'json' for structured data, 'markdown' for human-readable"
    )


class SearchPolicyInput(BaseModel):
    """Input model for policy search."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    query: str = Field(
        ...,
        description="Natural language query about company policy (e.g., 'first class flight rules')",
        min_length=3,
        max_length=500
    )
    max_results: int = Field(
        default=3,
        description="Maximum number of policy sections to return",
        ge=1,
        le=10
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'json' for structured data, 'markdown' for human-readable"
    )


class CheckApprovalInput(BaseModel):
    """Input model for approval threshold check."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    employee_id: str = Field(
        ...,
        description="Employee ID requesting the expense",
        pattern=r"^emp\d{3}$"
    )
    amount: float = Field(
        ...,
        description="Expense amount in USD",
        gt=0,
        le=1000000  # Sanity limit
    )
    expense_type: str = Field(
        ...,
        description="Type of expense (e.g., 'travel', 'software', 'equipment', 'client_entertainment')",
        min_length=1,
        max_length=100
    )


# =============================================================================
# Tool Implementations
# =============================================================================

@mcp.tool(
    name="policy_get_employee_info",
    annotations=ToolAnnotations(
        title="Get Employee Information",
        readOnlyHint=True,      # Does not modify data
        destructiveHint=False,   # No destructive operations
        idempotentHint=True,     # Same input = same output
        openWorldHint=False      # Closed system (our DB only)
    )
)
async def get_employee_info(params: GetEmployeeInput) -> str:
    """
    Retrieve employee information including level, title, and department.
    
    Use this tool to determine an employee's corporate level before
    checking policy permissions. Employee level determines approval
    authority and expense limits.
    
    Args:
        params: GetEmployeeInput containing:
            - employee_id (str): Employee ID like 'emp001'
            - response_format (ResponseFormat): Output format preference
    
    Returns:
        str: Employee information in requested format, or error message
    """
    employee = EMPLOYEE_DATABASE.get(params.employee_id)
    
    if not employee:
        return f"Error: Employee '{params.employee_id}' not found. Valid IDs: {', '.join(EMPLOYEE_DATABASE.keys())}"
    
    if params.response_format == ResponseFormat.JSON:
        import json
        return json.dumps(employee, indent=2)
    
    # Markdown format
    return f"""## Employee Information

**Name:** {employee['name']}  
**ID:** {employee['id']}  
**Title:** {employee['title']}  
**Level:** {employee['level']} ({_level_to_category(employee['level'])})  
**Department:** {employee['department']}  
**Manager ID:** {employee['manager_id']}
"""


@mcp.tool(
    name="policy_search_manual",
    annotations=ToolAnnotations(
        title="Search Policy Manual",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def search_policy_manual(params: SearchPolicyInput) -> str:
    """
    Search the corporate policy manual for relevant sections.
    
    Uses semantic search (RAG) to find policy sections matching the query.
    Returns confidence scores - if confidence is low, the information
    may not be reliable and you should say "I don't have enough information."
    
    Args:
        params: SearchPolicyInput containing:
            - query (str): Natural language query about policy
            - max_results (int): Maximum results to return (1-10)
            - response_format (ResponseFormat): Output format preference
    
    Returns:
        str: Relevant policy sections with confidence scores
    """
    results, is_confident = search_policies(params.query)
    
    # Limit results
    results = results[:params.max_results]
    
    if params.response_format == ResponseFormat.JSON:
        import json
        return json.dumps({
            "query": params.query,
            "is_confident": is_confident,
            "confidence_threshold": RETRIEVAL_CONFIDENCE_THRESHOLD,
            "results": results
        }, indent=2)
    
    # Markdown format
    confidence_warning = "" if is_confident else """
⚠️ **Low Confidence Warning**: No results met the confidence threshold.
The following results may not be relevant to your query.

"""
    
    sections = []
    for r in results:
        confidence_indicator = "✓" if r["is_confident"] else "⚠️"
        sections.append(f"""### {confidence_indicator} {r['title']}
**Category:** {r['category']} | **Confidence:** {r['score']:.2%} | **ID:** {r['id']}

{r['content']}
""")
    
    return f"""## Policy Search Results

**Query:** {params.query}  
**Confident Match:** {"Yes" if is_confident else "No"}

{confidence_warning}{"---".join(sections)}"""


@mcp.tool(
    name="policy_check_approval_threshold",
    annotations=ToolAnnotations(
        title="Check Approval Requirements",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def check_approval_threshold(params: CheckApprovalInput) -> str:
    """
    Determine the approval requirements for an expense.
    
    Based on the expense amount and employee level, determines:
    - Whether the employee can self-approve
    - Who needs to approve the expense
    - Any special requirements for the expense type
    
    Args:
        params: CheckApprovalInput containing:
            - employee_id (str): Employee requesting expense
            - amount (float): Expense amount in USD
            - expense_type (str): Category of expense
    
    Returns:
        str: JSON with approval requirements and recommendations
    """
    import json
    
    employee = EMPLOYEE_DATABASE.get(params.employee_id)
    if not employee:
        return json.dumps({
            "error": f"Employee '{params.employee_id}' not found",
            "valid_ids": list(EMPLOYEE_DATABASE.keys())
        })
    
    # Determine approval level needed
    if params.amount < 500:
        required_level = "Direct Manager"
        min_approver_level = employee["level"] + 1
    elif params.amount < 2000:
        required_level = "Department Head"
        min_approver_level = 7  # Senior Manager
    elif params.amount < 10000:
        required_level = "VP"
        min_approver_level = 11
    else:
        required_level = "CFO"
        min_approver_level = 13
    
    # Check if employee can approve at their level
    can_self_approve = False  # Self-approval always prohibited
    
    result = {
        "employee": {
            "id": employee["id"],
            "name": employee["name"],
            "level": employee["level"],
            "level_category": _level_to_category(employee["level"])
        },
        "expense": {
            "amount": params.amount,
            "type": params.expense_type,
            "formatted_amount": f"${params.amount:,.2f}"
        },
        "approval_requirements": {
            "required_approver_level": required_level,
            "minimum_approver_level_number": min_approver_level,
            "can_self_approve": can_self_approve,
            "reason": "Self-approval of expenses is prohibited at all levels per policy approval-002"
        },
        "recommendation": _get_approval_recommendation(
            employee["level"], 
            params.amount, 
            params.expense_type
        )
    }
    
    return json.dumps(result, indent=2)


# =============================================================================
# Helper Functions
# =============================================================================

def _level_to_category(level: int) -> str:
    """Convert numeric level to category name."""
    if level <= 3:
        return "Individual Contributor"
    elif level <= 6:
        return "Senior Individual Contributor"
    elif level <= 8:
        return "Senior Manager"
    elif level <= 10:
        return "Director"
    elif level <= 12:
        return "Vice President"
    else:
        return "Senior Vice President+"


def _get_approval_recommendation(_level: int, amount: float, expense_type: str) -> str:
    """Generate approval recommendation based on context."""
    if amount > 10000:
        return f"This ${amount:,.2f} expense requires CFO approval. Recommend discussing with your VP before submitting."
    elif amount > 2000:
        return f"This expense requires VP approval. Ensure you have documented business justification."
    elif expense_type.lower() in ["travel", "flight", "hotel"]:
        return "Travel expenses should be booked through the corporate travel portal when possible."
    elif expense_type.lower() in ["software", "equipment"]:
        return "Software and equipment purchases must be on the approved vendor list. Check with IT procurement."
    else:
        return "Standard approval process applies. Submit through the expense system with receipts."


# =============================================================================
# Server Entry Point
# =============================================================================

if __name__ == "__main__":
    # Run as stdio server for Claude Desktop integration
    mcp.run()
