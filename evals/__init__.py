"""
Evaluation package for Policy Enforcer.

Usage:
    python -m evals.run_evals --mock  # Run with mock agent
    python -m evals.run_evals         # Run with real API
"""

from .test_cases import TEST_CASES, TestCase, TestCategory
from .grader import EvalGrader, GradeResult
from .run_evals import EvalRunner, EvalReport
