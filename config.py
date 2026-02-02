"""
Configuration and constants for the Policy Enforcer.

Note: Never hardcode API keys. Always use environment variables.
"""

import os
from typing import Final

# =============================================================================
# API Configuration
# =============================================================================

ANTHROPIC_API_KEY: Final[str] = os.getenv("ANTHROPIC_API_KEY", "")
VOYAGE_API_KEY: Final[str] = os.getenv("VOYAGE_API_KEY", "")

# Model selection
# Note: Use Sonnet for most tasks (cost-effective), Opus for complex reasoning
CLAUDE_MODEL: Final[str] = "claude-sonnet-4-20250514"
CLAUDE_MODEL_FAST: Final[str] = "claude-haiku-4-20250514"  # For evals/grading
VOYAGE_MODEL: Final[str] = "voyage-3"  # SOTA for enterprise/legal/finance

# =============================================================================
# RAG Configuration
# =============================================================================

# Confidence threshold for retrieval
# Note: If similarity score is below this, refuse to answer rather than hallucinate
RETRIEVAL_CONFIDENCE_THRESHOLD: Final[float] = 0.75

# Number of chunks to retrieve
TOP_K_CHUNKS: Final[int] = 3

# Chunk size for document splitting (in characters)
CHUNK_SIZE: Final[int] = 500
CHUNK_OVERLAP: Final[int] = 50

# =============================================================================
# Rate Limiting
# =============================================================================

MAX_REQUESTS_PER_MINUTE: Final[int] = 60
MAX_TOKENS_PER_REQUEST: Final[int] = 4096

# =============================================================================
# Guardrails Configuration
# =============================================================================

# Maximum input length (characters)
MAX_INPUT_LENGTH: Final[int] = 2000

# Patterns that indicate prompt injection attempts
INJECTION_PATTERNS: Final[list[str]] = [
    "ignore previous instructions",
    "ignore all instructions",
    "disregard your instructions",
    "forget your rules",
    "you are now",
    "act as if",
    "pretend you are",
    "new instructions:",
    "system prompt:",
    "override:",
]

# =============================================================================
# Data Configuration
# =============================================================================

from pathlib import Path

# Paths to data files
DATA_DIR = Path(__file__).parent / "data"
EMPLOYEES_FILE = DATA_DIR / "employees.json"
RULES_FILE = DATA_DIR / "rules.json"

# =============================================================================
# Validation
# =============================================================================

def validate_config() -> None:
    """Validate that required configuration is present."""
    if not ANTHROPIC_API_KEY:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is required. "
            "Set it with: export ANTHROPIC_API_KEY='your-key'"
        )
    # Voyage is optional - we can fall back to Claude for embeddings
    if not VOYAGE_API_KEY:
        print("Warning: VOYAGE_API_KEY not set. Using mock embeddings.")
