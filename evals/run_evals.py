"""
Evaluation Runner: Execute Tests and Generate Reports

Concepts Demonstrated:
1. Systematic evaluation execution
2. Progress tracking and reporting
3. Failure analysis and categorization
4. Regression detection
"""

import sys
import json
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from test_cases import TEST_CASES, TestCase, TestCategory
from grader import EvalGrader, GradeResult

# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class EvalResult:
    """Result for a single evaluation."""
    test_case: TestCase
    response_text: str
    parsed_approved: Optional[bool]
    parsed_policy_ref: Optional[str]
    parsed_confidence: Optional[float]
    parsed_escalation: Optional[bool]
    grade: Optional[GradeResult]
    duration_ms: float
    error: Optional[str] = None


@dataclass 
class EvalReport:
    """Summary report for an evaluation run."""
    timestamp: str
    total_tests: int
    passed: int
    failed: int
    errors: int
    pass_rate: float
    avg_score: float
    avg_duration_ms: float
    by_category: dict
    failures: list[dict]


# =============================================================================
# Mock Agent for Testing Without API
# =============================================================================

class MockAgent:
    """
    Mock agent for testing the eval harness without API calls.
    
    Note: Always have a way to test your eval pipeline
    without making real API calls. This saves money and allows
    fast iteration on the eval framework itself.
    """
    
    def run(self, query: str, employee_id: str) -> dict:
        """Return a mock response for testing."""
        # Simple heuristic-based mock
        query_lower = query.lower()
        
        approved = False
        policy_ref = "unknown"
        confidence = 0.85
        escalation = False
        
        if "first class" in query_lower:
            approved = False
            policy_ref = "travel-001"
            if "director" in query_lower or "vp" in query_lower:
                approved = True
                escalation = True
        elif "business class" in query_lower:
            if "domestic" in query_lower or "nyc" in query_lower or "la" in query_lower:
                approved = False
            policy_ref = "travel-001"
        elif "hotel" in query_lower:
            policy_ref = "travel-002"
            approved = True
        elif "meal" in query_lower or "dinner" in query_lower:
            policy_ref = "expense-001"
            approved = True
        elif "software" in query_lower:
            policy_ref = "expense-002"
            approved = True
        elif "approve" in query_lower and "own" in query_lower:
            approved = False
            policy_ref = "approval-002"
            confidence = 0.95
        
        return {
            "approved": approved,
            "reason": f"Mock response for: {query[:50]}...",
            "policy_reference": policy_ref,
            "confidence": confidence,
            "requires_escalation": escalation
        }


# =============================================================================
# Evaluation Runner
# =============================================================================

class EvalRunner:
    """
    Run evaluations against the policy agent.
    
    Usage:
        runner = EvalRunner()
        report = runner.run_all()
        runner.print_report(report)
    """
    
    def __init__(self, use_mock: bool = False):
        """
        Initialize the runner.
        
        Args:
            use_mock: If True, use mock agent instead of real API
        """
        self.use_mock = use_mock
        self.grader = EvalGrader()
        
        if use_mock:
            self.agent = MockAgent()
        else:
            # Import real agent
            try:
                from agent import PolicyAgent
                self.agent = PolicyAgent()
            except Exception as e:
                print(f"Warning: Could not load PolicyAgent ({e}), using mock")
                self.agent = MockAgent()
                self.use_mock = True
    
    def run_single(self, test_case: TestCase) -> EvalResult:
        """Run a single test case."""
        start_time = time.time()
        
        try:
            # Run the agent
            if self.use_mock:
                response = self.agent.run(test_case.query, test_case.employee_id)
                response_text = json.dumps(response)
            else:
                # Real agent - construct query with employee context
                full_query = f"Employee {test_case.employee_id}: {test_case.query}"
                agent_response = self.agent.run(full_query)
                response_text = agent_response.raw_response
                
                # Try to get structured response
                if agent_response.structured_response:
                    response = {
                        "approved": agent_response.structured_response.approved,
                        "policy_reference": agent_response.structured_response.policy_reference,
                        "confidence": agent_response.structured_response.confidence,
                        "requires_escalation": agent_response.structured_response.requires_escalation
                    }
                else:
                    response = self._parse_response(response_text)
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract values
            parsed_approved = response.get("approved")
            parsed_policy_ref = response.get("policy_reference")
            parsed_confidence = response.get("confidence")
            parsed_escalation = response.get("requires_escalation")
            
            # Grade the response
            grade = self.grader._rule_based_grade(
                test_id=test_case.id,
                expected_approved=test_case.expected_approved,
                expected_policy_ref=test_case.expected_policy_ref,
                expected_escalation=test_case.expected_escalation,
                min_confidence=test_case.min_confidence,
                actual_approved=parsed_approved,
                actual_policy_ref=parsed_policy_ref,
                actual_confidence=parsed_confidence,
                actual_escalation=parsed_escalation
            )
            
            return EvalResult(
                test_case=test_case,
                response_text=response_text,
                parsed_approved=parsed_approved,
                parsed_policy_ref=parsed_policy_ref,
                parsed_confidence=parsed_confidence,
                parsed_escalation=parsed_escalation,
                grade=grade,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return EvalResult(
                test_case=test_case,
                response_text="",
                parsed_approved=None,
                parsed_policy_ref=None,
                parsed_confidence=None,
                parsed_escalation=None,
                grade=None,
                duration_ms=duration_ms,
                error=str(e)
            )
    
    def _parse_response(self, response_text: str) -> dict:
        """Parse structured response from text."""
        import re
        
        try:
            # Try to find JSON in markdown code block
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Try to parse as plain JSON
            return json.loads(response_text)
        except:
            return {}
    
    def run_all(self, categories: Optional[list[TestCategory]] = None) -> EvalReport:
        """
        Run all test cases (or filtered by category).
        
        Args:
            categories: Optional list of categories to filter
            
        Returns:
            EvalReport with summary statistics
        """
        # Filter test cases
        test_cases = TEST_CASES
        if categories:
            test_cases = [tc for tc in test_cases if tc.category in categories]
        
        results: list[EvalResult] = []
        passed = 0
        failed = 0
        errors = 0
        total_score = 0.0
        total_duration = 0.0
        by_category: dict[str, dict] = {}
        failures: list[dict] = []
        
        print(f"\nRunning {len(test_cases)} test cases...")
        print("=" * 60)
        
        for i, tc in enumerate(test_cases):
            # Progress indicator
            print(f"[{i+1}/{len(test_cases)}] {tc.id}: {tc.description[:40]}...", end=" ")
            
            result = self.run_single(tc)
            results.append(result)
            total_duration += result.duration_ms
            
            # Track by category
            cat = tc.category.value
            if cat not in by_category:
                by_category[cat] = {"total": 0, "passed": 0, "failed": 0}
            by_category[cat]["total"] += 1
            
            if result.error:
                errors += 1
                print("❌ ERROR")
                failures.append({
                    "test_id": tc.id,
                    "type": "error",
                    "message": result.error
                })
            elif result.grade and result.grade.passed:
                passed += 1
                total_score += result.grade.score
                by_category[cat]["passed"] += 1
                print(f"✓ PASS ({result.grade.score:.0%})")
            else:
                failed += 1
                by_category[cat]["failed"] += 1
                score = result.grade.score if result.grade else 0
                total_score += score
                print(f"✗ FAIL ({score:.0%})")
                failures.append({
                    "test_id": tc.id,
                    "type": "failure",
                    "expected_approved": tc.expected_approved,
                    "actual_approved": result.parsed_approved,
                    "expected_policy": tc.expected_policy_ref,
                    "actual_policy": result.parsed_policy_ref,
                    "score": score
                })
        
        total_tests = len(test_cases)
        pass_rate = passed / total_tests if total_tests > 0 else 0
        avg_score = total_score / total_tests if total_tests > 0 else 0
        avg_duration = total_duration / total_tests if total_tests > 0 else 0
        
        return EvalReport(
            timestamp=datetime.now().isoformat(),
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            errors=errors,
            pass_rate=pass_rate,
            avg_score=avg_score,
            avg_duration_ms=avg_duration,
            by_category=by_category,
            failures=failures
        )
    
    def print_report(self, report: EvalReport) -> None:
        """Print a formatted report."""
        print("\n" + "=" * 60)
        print("EVALUATION REPORT")
        print("=" * 60)
        print(f"Timestamp: {report.timestamp}")
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed} ({report.pass_rate:.1%})")
        print(f"Failed: {report.failed}")
        print(f"Errors: {report.errors}")
        print(f"Average Score: {report.avg_score:.1%}")
        print(f"Average Duration: {report.avg_duration_ms:.0f}ms")
        
        print("\n--- By Category ---")
        for cat, stats in report.by_category.items():
            cat_rate = stats["passed"] / stats["total"] if stats["total"] > 0 else 0
            print(f"  {cat}: {stats['passed']}/{stats['total']} ({cat_rate:.0%})")
        
        if report.failures:
            print("\n--- Failures ---")
            for f in report.failures[:5]:  # Show first 5
                print(f"  {f['test_id']}: {f.get('type', 'unknown')}")
                if f.get("type") == "failure":
                    print(f"    Expected: approved={f.get('expected_approved')}, policy={f.get('expected_policy')}")
                    print(f"    Actual: approved={f.get('actual_approved')}, policy={f.get('actual_policy')}")
        
        # Pass/Fail summary
        print("\n" + "=" * 60)
        if report.pass_rate >= 0.9:
            print("✓ OVERALL: PASS (≥90% pass rate)")
        elif report.pass_rate >= 0.7:
            print("⚠ OVERALL: MARGINAL (70-90% pass rate)")
        else:
            print("✗ OVERALL: FAIL (<70% pass rate)")
        print("=" * 60)
    
    def save_report(self, report: EvalReport, path: str = "eval_report.json") -> None:
        """Save report to JSON file."""
        # Convert dataclass to dict
        report_dict = {
            "timestamp": report.timestamp,
            "total_tests": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
            "errors": report.errors,
            "pass_rate": report.pass_rate,
            "avg_score": report.avg_score,
            "avg_duration_ms": report.avg_duration_ms,
            "by_category": report.by_category,
            "failures": report.failures
        }
        
        with open(path, "w") as f:
            json.dump(report_dict, f, indent=2)
        
        print(f"\nReport saved to: {path}")


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Run evaluations from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run policy enforcer evaluations")
    parser.add_argument("--mock", action="store_true", help="Use mock agent instead of real API")
    parser.add_argument("--category", type=str, help="Filter by category (travel, expense, approval, edge_case, negative)")
    parser.add_argument("--output", type=str, default="eval_report.json", help="Output file path")
    
    args = parser.parse_args()
    
    # Parse category filter
    categories = None
    if args.category:
        try:
            categories = [TestCategory(args.category)]
        except ValueError:
            print(f"Invalid category: {args.category}")
            print(f"Valid categories: {[c.value for c in TestCategory]}")
            return
    
    # Run evaluations
    runner = EvalRunner(use_mock=args.mock)
    report = runner.run_all(categories=categories)
    
    # Print and save report
    runner.print_report(report)
    runner.save_report(report, args.output)


if __name__ == "__main__":
    main()
