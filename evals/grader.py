"""
Grader: LLM-as-Judge for Evaluation

FDE-Level Concepts Demonstrated:
1. Using a cheaper/faster model for grading
2. Structured grading criteria
3. Explanation extraction for debugging
4. Partial credit scoring
"""

import json
from dataclasses import dataclass
from typing import Optional

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from config import CLAUDE_MODEL_FAST
except ImportError:
    CLAUDE_MODEL_FAST = "claude-haiku-4-20250514"

# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class GradeResult:
    """Result from grading a single test case."""
    test_id: str
    passed: bool
    score: float  # 0.0 to 1.0
    explanation: str
    details: dict


# =============================================================================
# Grading Prompts
# =============================================================================

GRADER_SYSTEM_PROMPT = """You are an evaluation grader for a Corporate Policy AI system. Your job is to compare the AI's response against expected outcomes and provide a structured grade.

You will receive:
1. The test case with expected outcomes
2. The AI's actual response

Grade based on these criteria:
- **Approval Match (40%)**: Did the AI give the correct approval/rejection decision?
- **Policy Reference (20%)**: Did the AI cite the correct policy?
- **Confidence Appropriate (20%)**: Is the confidence score reasonable for this case?
- **Escalation Correct (20%)**: Did the AI correctly identify if escalation is needed?

Respond with JSON only:
```json
{
  "passed": boolean (true if score >= 0.7),
  "score": float (0.0 to 1.0),
  "approval_correct": boolean,
  "policy_correct": boolean,
  "confidence_appropriate": boolean,
  "escalation_correct": boolean,
  "explanation": "Brief explanation of the grade"
}
```"""


# =============================================================================
# Grader Implementation
# =============================================================================

class EvalGrader:
    """
    LLM-based grader for policy decisions.
    
    FDE Note: We use Haiku (fast/cheap) for grading because:
    1. Grading is a simpler task than generation
    2. We run many evals, cost matters
    3. Speed matters for rapid iteration
    """
    
    def __init__(self):
        if ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic()
            self.model = CLAUDE_MODEL_FAST
        else:
            self.client = None
            self.model = None
    
    def grade(
        self,
        test_id: str,
        query: str,
        expected_approved: bool,
        expected_policy_ref: str,
        expected_escalation: bool,
        min_confidence: float,
        actual_response: str,
        actual_approved: Optional[bool],
        actual_policy_ref: Optional[str],
        actual_confidence: Optional[float],
        actual_escalation: Optional[bool]
    ) -> GradeResult:
        """
        Grade a single response against expected outcomes.
        
        Args:
            test_id: Identifier for this test case
            query: The original query
            expected_*: Expected values from test case
            actual_*: Actual values from AI response
        
        Returns:
            GradeResult with score and explanation
        """
        # Build grading prompt
        grading_prompt = f"""## Test Case: {test_id}

**Query:** {query}

### Expected Outcomes
- Approved: {expected_approved}
- Policy Reference: {expected_policy_ref}
- Minimum Confidence: {min_confidence}
- Requires Escalation: {expected_escalation}

### Actual AI Response
- Approved: {actual_approved}
- Policy Reference: {actual_policy_ref}
- Confidence: {actual_confidence}
- Requires Escalation: {actual_escalation}

**Full Response:**
{actual_response[:1500]}  # Truncate for efficiency

Please grade this response."""

        # If no API available, use rule-based grading
        if not self.client:
            return self._rule_based_grade(
                test_id, expected_approved, expected_policy_ref,
                expected_escalation, min_confidence,
                actual_approved, actual_policy_ref,
                actual_confidence, actual_escalation
            )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                system=GRADER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": grading_prompt}]
            )
            
            # Parse the grading response
            response_text = response.content[0].text
            
            # Extract JSON from response
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                grade_data = json.loads(json_match.group(1))
            else:
                # Try parsing the whole response as JSON
                grade_data = json.loads(response_text)
            
            return GradeResult(
                test_id=test_id,
                passed=grade_data.get("passed", False),
                score=grade_data.get("score", 0.0),
                explanation=grade_data.get("explanation", ""),
                details={
                    "approval_correct": grade_data.get("approval_correct"),
                    "policy_correct": grade_data.get("policy_correct"),
                    "confidence_appropriate": grade_data.get("confidence_appropriate"),
                    "escalation_correct": grade_data.get("escalation_correct"),
                }
            )
            
        except Exception as e:
            # Fallback to rule-based grading if LLM fails
            return self._rule_based_grade(
                test_id, expected_approved, expected_policy_ref,
                expected_escalation, min_confidence,
                actual_approved, actual_policy_ref,
                actual_confidence, actual_escalation
            )
    
    def _rule_based_grade(
        self,
        test_id: str,
        expected_approved: bool,
        expected_policy_ref: str,
        expected_escalation: bool,
        min_confidence: float,
        actual_approved: Optional[bool],
        actual_policy_ref: Optional[str],
        actual_confidence: Optional[float],
        actual_escalation: Optional[bool]
    ) -> GradeResult:
        """
        Fallback rule-based grading.
        
        FDE Note: Always have a fallback. LLM grading can fail,
        and you don't want your eval pipeline to break.
        """
        score = 0.0
        details = {}
        
        # Approval match (40%)
        if actual_approved == expected_approved:
            score += 0.4
            details["approval_correct"] = True
        else:
            details["approval_correct"] = False
        
        # Policy reference (20%)
        if actual_policy_ref and expected_policy_ref != "N/A":
            if actual_policy_ref == expected_policy_ref:
                score += 0.2
                details["policy_correct"] = True
            elif expected_policy_ref in str(actual_policy_ref):
                score += 0.1  # Partial credit
                details["policy_correct"] = "partial"
            else:
                details["policy_correct"] = False
        else:
            details["policy_correct"] = None
        
        # Confidence (20%)
        if actual_confidence is not None:
            if actual_confidence >= min_confidence:
                score += 0.2
                details["confidence_appropriate"] = True
            elif actual_confidence >= min_confidence - 0.2:
                score += 0.1  # Partial credit
                details["confidence_appropriate"] = "partial"
            else:
                details["confidence_appropriate"] = False
        else:
            details["confidence_appropriate"] = None
        
        # Escalation (20%)
        if actual_escalation == expected_escalation:
            score += 0.2
            details["escalation_correct"] = True
        else:
            details["escalation_correct"] = False
        
        passed = score >= 0.7
        
        return GradeResult(
            test_id=test_id,
            passed=passed,
            score=score,
            explanation=f"Rule-based grade: {score:.0%}",
            details=details
        )


# =============================================================================
# Batch Grading
# =============================================================================

def grade_batch(results: list[dict]) -> list[GradeResult]:
    """
    Grade a batch of test results.
    
    Args:
        results: List of dicts with test case info and actual responses
        
    Returns:
        List of GradeResults
    """
    grader = EvalGrader()
    grades = []
    
    for result in results:
        grade = grader.grade(
            test_id=result["test_id"],
            query=result["query"],
            expected_approved=result["expected_approved"],
            expected_policy_ref=result["expected_policy_ref"],
            expected_escalation=result.get("expected_escalation", False),
            min_confidence=result["min_confidence"],
            actual_response=result.get("actual_response", ""),
            actual_approved=result.get("actual_approved"),
            actual_policy_ref=result.get("actual_policy_ref"),
            actual_confidence=result.get("actual_confidence"),
            actual_escalation=result.get("actual_escalation"),
        )
        grades.append(grade)
    
    return grades


# =============================================================================
# Demo
# =============================================================================

if __name__ == "__main__":
    # Quick test of the grader
    grader = EvalGrader()
    
    result = grader._rule_based_grade(
        test_id="test-001",
        expected_approved=False,
        expected_policy_ref="travel-001",
        expected_escalation=False,
        min_confidence=0.8,
        actual_approved=False,
        actual_policy_ref="travel-001",
        actual_confidence=0.92,
        actual_escalation=False
    )
    
    print(f"Test: {result.test_id}")
    print(f"Passed: {result.passed}")
    print(f"Score: {result.score:.0%}")
    print(f"Details: {result.details}")
