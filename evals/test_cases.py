"""
Evaluation Test Cases: Golden Dataset for Policy Enforcer

FDE-Level Concepts Demonstrated:
1. Diverse test cases covering edge cases
2. Expected outputs with reasoning
3. Categories for targeted testing
4. Negative tests (things that should fail)
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class TestCategory(str, Enum):
    """Categories of test cases."""
    TRAVEL = "travel"
    EXPENSE = "expense"
    APPROVAL = "approval"
    EDGE_CASE = "edge_case"
    NEGATIVE = "negative"  # Should be rejected/escalated


@dataclass
class TestCase:
    """A single test case for evaluation."""
    id: str
    category: TestCategory
    query: str
    employee_id: str
    expected_approved: bool
    expected_policy_ref: str
    min_confidence: float
    description: str
    expected_escalation: bool = False


# =============================================================================
# Test Cases
# =============================================================================

TEST_CASES = [
    # ==========================================================================
    # TRAVEL TESTS
    # ==========================================================================
    TestCase(
        id="travel-001",
        category=TestCategory.TRAVEL,
        query="Can I fly first class to London? It's an 8-hour flight.",
        employee_id="emp001",  # Level 5 - Senior IC
        expected_approved=False,
        expected_policy_ref="travel-001",
        min_confidence=0.8,
        description="Level 5 employee cannot fly first class (requires Level 9+)"
    ),
    
    TestCase(
        id="travel-002",
        category=TestCategory.TRAVEL,
        query="Can I fly first class to London? It's an 8-hour flight.",
        employee_id="emp002",  # Level 9 - Director
        expected_approved=True,  # Meets level requirement, but needs VP pre-approval
        expected_policy_ref="travel-001",
        min_confidence=0.7,
        description="Level 9 Director qualifies for first class on 8+ hour international",
        expected_escalation=True  # VP pre-approval required
    ),
    
    TestCase(
        id="travel-003",
        category=TestCategory.TRAVEL,
        query="Can I fly business class from NYC to LA?",
        employee_id="emp002",  # Level 9 - Director
        expected_approved=False,
        expected_policy_ref="travel-001",
        min_confidence=0.8,
        description="Domestic flights are economy only regardless of level"
    ),
    
    TestCase(
        id="travel-004",
        category=TestCategory.TRAVEL,
        query="Can I fly business class to Tokyo? It's a 14-hour flight.",
        employee_id="emp001",  # Level 5 - Senior IC
        expected_approved=False,
        expected_policy_ref="travel-001",
        min_confidence=0.8,
        description="Level 5 doesn't qualify for business class (requires Level 7+)"
    ),
    
    TestCase(
        id="travel-005",
        category=TestCategory.TRAVEL,
        query="Can I book a hotel for $350 per night in NYC?",
        employee_id="emp001",  # Level 5
        expected_approved=False,
        expected_policy_ref="travel-002",
        min_confidence=0.8,
        description="$350 exceeds domestic hotel limit of $200 for non-Directors"
    ),
    
    TestCase(
        id="travel-006",
        category=TestCategory.TRAVEL,
        query="Can I book a hotel for $350 per night in London?",
        employee_id="emp002",  # Level 9 - Director
        expected_approved=True,
        expected_policy_ref="travel-002",
        min_confidence=0.8,
        description="Directors can book up to $400/night, $350 international is within limit"
    ),
    
    # ==========================================================================
    # EXPENSE TESTS
    # ==========================================================================
    TestCase(
        id="expense-001",
        category=TestCategory.EXPENSE,
        query="Can I expense a $100 dinner during my business trip?",
        employee_id="emp001",
        expected_approved=False,
        expected_policy_ref="expense-001",
        min_confidence=0.8,
        description="$100 exceeds domestic dinner limit of $50"
    ),
    
    TestCase(
        id="expense-002",
        category=TestCategory.EXPENSE,
        query="Can I expense meals totaling $70 today while traveling domestically?",
        employee_id="emp001",
        expected_approved=True,
        expected_policy_ref="expense-001",
        min_confidence=0.8,
        description="$70 is within the $75 daily domestic meal limit"
    ),
    
    TestCase(
        id="expense-003",
        category=TestCategory.EXPENSE,
        query="Can I expense a bottle of wine ($45) from a client dinner?",
        employee_id="emp001",
        expected_approved=False,
        expected_policy_ref="expense-001",
        min_confidence=0.7,
        description="Alcohol not reimbursable without prior approval for client entertainment"
    ),
    
    TestCase(
        id="expense-004",
        category=TestCategory.EXPENSE,
        query="Can I buy $400 software for my project?",
        employee_id="emp001",  # Level 5
        expected_approved=True,
        expected_policy_ref="expense-002",
        min_confidence=0.8,
        description="Software under $500 can be approved by direct manager"
    ),
    
    TestCase(
        id="expense-005",
        category=TestCategory.EXPENSE,
        query="Can I purchase $1500 software for my team?",
        employee_id="emp004",  # Level 3 - IC
        expected_approved=False,  # Not self-approved, needs Dept Head
        expected_policy_ref="expense-002",
        min_confidence=0.8,
        description="$1500 software needs Department Head approval",
        expected_escalation=True
    ),
    
    # ==========================================================================
    # APPROVAL TESTS
    # ==========================================================================
    TestCase(
        id="approval-001",
        category=TestCategory.APPROVAL,
        query="Can I approve a $300 expense for my direct report?",
        employee_id="emp001",  # Level 5 - has direct reports
        expected_approved=True,
        expected_policy_ref="approval-001",
        min_confidence=0.8,
        description="$300 under $500 threshold, manager can approve"
    ),
    
    TestCase(
        id="approval-002",
        category=TestCategory.APPROVAL,
        query="Can I approve my own $200 expense?",
        employee_id="emp002",  # Level 9 - Director
        expected_approved=False,
        expected_policy_ref="approval-002",
        min_confidence=0.9,
        description="Self-approval prohibited at all levels"
    ),
    
    TestCase(
        id="approval-003",
        category=TestCategory.APPROVAL,
        query="Can I approve a $8000 equipment purchase for my team?",
        employee_id="emp002",  # Level 9 - Director
        expected_approved=False,
        expected_policy_ref="approval-001",
        min_confidence=0.8,
        description="$8000 requires VP approval (Level 11+), Director cannot approve",
        expected_escalation=True
    ),
    
    TestCase(
        id="approval-004",
        category=TestCategory.APPROVAL,
        query="Can I approve a $15000 contract?",
        employee_id="emp003",  # Level 11 - VP
        expected_approved=False,
        expected_policy_ref="approval-001",
        min_confidence=0.8,
        description="$15000 exceeds $10000 threshold, requires CFO approval",
        expected_escalation=True
    ),
    
    # ==========================================================================
    # EDGE CASES
    # ==========================================================================
    TestCase(
        id="edge-001",
        category=TestCategory.EDGE_CASE,
        query="I had an emergency and spent $800 without pre-approval. Can I submit it?",
        employee_id="emp001",
        expected_approved=True,  # Policy allows post-facto for emergencies up to $1000
        expected_policy_ref="approval-001",
        min_confidence=0.7,
        description="Emergency expenses up to $1000 can be submitted post-facto",
        expected_escalation=True  # Needs documented justification
    ),
    
    TestCase(
        id="edge-002",
        category=TestCategory.EDGE_CASE,
        query="Can I expense gym membership for my home office?",
        employee_id="emp001",
        expected_approved=False,
        expected_policy_ref="compliance-002",
        min_confidence=0.8,
        description="Gym memberships explicitly prohibited in compliance policy"
    ),
    
    TestCase(
        id="edge-003",
        category=TestCategory.EDGE_CASE,
        query="Can my spouse fly with me to the company conference?",
        employee_id="emp002",
        expected_approved=False,
        expected_policy_ref="compliance-002",
        min_confidence=0.7,
        description="Spouse travel requires pre-approval for specific events",
        expected_escalation=True
    ),
    
    # ==========================================================================
    # NEGATIVE TESTS (Should be rejected or escalated)
    # ==========================================================================
    TestCase(
        id="negative-001",
        category=TestCategory.NEGATIVE,
        query="What's the policy on bringing pets to the office?",
        employee_id="emp001",
        expected_approved=False,
        expected_policy_ref="N/A",
        min_confidence=0.0,  # Should have low confidence (not in our policies)
        description="Query outside scope of expense/travel policies",
        expected_escalation=True
    ),
    
    TestCase(
        id="negative-002",
        category=TestCategory.NEGATIVE,
        query="Can I donate company money to my friend's political campaign?",
        employee_id="emp001",
        expected_approved=False,
        expected_policy_ref="compliance-002",
        min_confidence=0.8,
        description="Political contributions explicitly prohibited"
    ),
]


# =============================================================================
# Helper Functions
# =============================================================================

def get_test_cases_by_category(category: TestCategory) -> list[TestCase]:
    """Get all test cases for a specific category."""
    return [tc for tc in TEST_CASES if tc.category == category]


def get_all_test_cases() -> list[TestCase]:
    """Get all test cases."""
    return TEST_CASES


def get_test_case_by_id(test_id: str) -> Optional[TestCase]:
    """Get a specific test case by ID."""
    for tc in TEST_CASES:
        if tc.id == test_id:
            return tc
    return None


# =============================================================================
# Summary Statistics
# =============================================================================

if __name__ == "__main__":
    print("Test Case Summary")
    print("=" * 50)
    
    total = len(TEST_CASES)
    by_category = {}
    expected_approvals = sum(1 for tc in TEST_CASES if tc.expected_approved)
    expected_escalations = sum(1 for tc in TEST_CASES if tc.expected_escalation)
    
    for tc in TEST_CASES:
        by_category[tc.category] = by_category.get(tc.category, 0) + 1
    
    print(f"Total test cases: {total}")
    print(f"Expected approvals: {expected_approvals}")
    print(f"Expected rejections: {total - expected_approvals}")
    print(f"Expected escalations: {expected_escalations}")
    print()
    print("By category:")
    for cat, count in by_category.items():
        print(f"  {cat.value}: {count}")
