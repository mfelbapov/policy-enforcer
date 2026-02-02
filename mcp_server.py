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
from config import (
    RETRIEVAL_CONFIDENCE_THRESHOLD,
    EMPLOYEES_FILE,
    RULES_FILE
)
import json

# =============================================================================
# Helper Functions
# =============================================================================

def _load_employees() -> dict:
    """Load employee data from JSON."""
    if not EMPLOYEES_FILE.exists():
        return {}
    
    with open(EMPLOYEES_FILE, "r") as f:
        data = json.load(f)
        # Convert list to dict keyed by ID
        return {emp["id"]: emp for emp in data.get("employees", [])}

def _load_rules() -> dict:
    """Load business rules from JSON."""
    if not RULES_FILE.exists():
        return {}
    
    with open(RULES_FILE, "r") as f:
        return json.load(f).get("approval_rules", {})

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

# =============================================================================
# Server Initialization
# =============================================================================

from mcp.server.fastmcp import FastMCP

# FDE Note: Server name follows convention: {service}_mcp
mcp = FastMCP("policy_enforcer_mcp")


# =============================================================================
# Tool Definitions (Claude API Format)
# =============================================================================

# FDE Note: Centralized source of truth for tool schemas.
# These match the @mcp.tool implementations below.
CLAUDE_TOOLS = [
    {
        "name": "policy_get_employee_info",
        "description": "Retrieve employee information including level, title, and department. Use this to determine an employee's corporate level before checking policy permissions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Employee ID (e.g., 'emp001', 'emp002')",
                    "pattern": "^emp\\d{3}$"
                },
                "response_format": {
                    "type": "string",
                    "enum": ["json", "markdown"],
                    "default": "json",
                    "description": "Output format preference"
                }
            },
            "required": ["employee_id"]
        }
    },
    {
        "name": "policy_search_manual",
        "description": "Search the corporate policy manual for relevant sections. Returns confidence scores - if confidence is low, say 'I don't have enough information.'",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query about company policy",
                    "minLength": 3,
                    "maxLength": 500
                },
                "max_results": {
                    "type": "integer",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum number of policy sections to return"
                },
                "response_format": {
                    "type": "string",
                    "enum": ["json", "markdown"],
                    "default": "json"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "policy_check_approval_threshold",
        "description": "Determine the approval requirements for an expense based on amount and employee level.",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Employee ID requesting the expense",
                    "pattern": "^emp\\d{3}$"
                },
                "amount": {
                    "type": "number",
                    "description": "Expense amount in USD",
                    "minimum": 0,
                    "maximum": 1000000
                },
                "expense_type": {
                    "type": "string",
                    "description": "Type of expense (e.g., 'travel', 'software', 'equipment')"
                }
            },
            "required": ["employee_id", "amount", "expense_type"]
        }
    }
]


def _get_approval_recommendation(_level: int, amount: float, expense_type: str, rules: dict) -> str:
    """Generate approval recommendation based on context."""
    # Logic extracted from rules if possible, but keeping recommendation text here mostly for now
    # as it constructs natural language.
    
    # Check max threshold in rules
    thresholds = rules.get("thresholds", [])
    if not thresholds:
        return "Standard approval process applies."
        
    sorted_thresholds = sorted(thresholds, key=lambda x: x["amount_limit"])
    
    # Special check for high values (VP/CFO level typically)
    highest_limit = sorted_thresholds[-1]["amount_limit"]
    
    if amount > highest_limit:
        default_role = rules.get("default_threshold", {}).get("role", "CFO")
        return f"This ${amount:,.2f} expense requires {default_role} approval. Recommend discussing with your VP before submitting."
    
    # Check other thresholds
    for t in sorted_thresholds:
        if amount > t["amount_limit"]:
            # Keep checking higher limits
            continue
        
        # If amount is just above previous limit but below this one, we effectively need this one's approval
        # Wait, the logic is "if amount < limit".
        pass

    # Reverting to simpler logic for recommendation string for now, as it's advisory
    if amount > 10000:
        return f"This ${amount:,.2f} expense requires high-level approval."
    elif expense_type.lower() in ["travel", "flight", "hotel"]:
        return "Travel expenses should be booked through the corporate travel portal when possible."
    elif expense_type.lower() in ["software", "equipment"]:
        return "Software and equipment purchases must be on the approved vendor list. Check with IT procurement."
    else:
        return "Standard approval process applies. Submit through the expense system with receipts."

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
    employee_db = _load_employees()
    employee = employee_db.get(params.employee_id)
    
    if not employee:
        return f"Error: Employee '{params.employee_id}' not found. Valid IDs: {', '.join(employee_db.keys())}"
    
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
    
    employee_db = _load_employees()
    employee = employee_db.get(params.employee_id)
    if not employee:
        return json.dumps({
            "error": f"Employee '{params.employee_id}' not found",
            "valid_ids": list(employee_db.keys())
        })
    
    # Load rules
    rules = _load_rules()
    
    # Determine approval level needed
    required_level = "Unknown"
    min_approver_level = 99
    
    # Default to catch-all (CFO)
    default_rule = rules.get("default_threshold", {"role": "CFO", "min_level_absolute": 13})
    required_level = default_rule.get("role")
    min_approver_level = default_rule.get("min_level_absolute")
    
    # Check increasingly strict thresholds
    # We sort by amount to find the *first* bucket the amount fits into (if any)
    # Actually, usually logic is "if amount < X".
    # So we sort by amount ascending. The first one that satisfies amount < limit is our guy.
    
    thresholds = sorted(rules.get("thresholds", []), key=lambda x: x["amount_limit"])
    
    for t in thresholds:
        if params.amount < t["amount_limit"]:
            required_level = t["role"]
            if "min_level_offset" in t:
                min_approver_level = employee["level"] + t["min_level_offset"]
            else:
                min_approver_level = t.get("min_level_absolute", 99)
            break
    
    # Check if employee can approve at their level
    can_self_approve = rules.get("general", {}).get("self_approval_allowed", False)
    reason = rules.get("general", {}).get("reason_self_approval", "Self-approval prohibited")
    
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
            "reason": reason
        },
        "recommendation": _get_approval_recommendation(
            employee["level"], 
            params.amount, 
            params.expense_type,
            rules
        )
    }
    
    return json.dumps(result, indent=2)


# =============================================================================
# Helper Functions
# =============================================================================




# =============================================================================
# Server Entry Point
# =============================================================================

if __name__ == "__main__":
    # Run as stdio server for Claude Desktop integration
    mcp.run()
