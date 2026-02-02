# Corporate Policy Enforcer

An AI agent that answers employee policy questions by retrieving relevant policies and reasoning through them — demonstrating production patterns for enterprise AI deployment.

**Example:** "Can I expense a first-class flight to London?"

The system identifies the employee's role, retrieves relevant policy sections, reasons through the rules, and returns a structured decision.

---

## Why I Built This

Enterprise AI isn't just about calling an LLM. It's about building systems that are reliable, auditable, and safe. This project demonstrates the patterns that matter for production deployment:

- **RAG** — Retrieve relevant context, not everything
- **Tool Use** — Let the model call functions when it needs information
- **Guardrails** — Validate inputs, catch prompt injection, enforce output structure
- **Evals** — Automated testing with LLM-as-judge to catch regressions
- **Structured Output** — JSON schema enforcement for downstream integration

---

## Architecture

```
User Question
      │
      ▼
┌─────────────────────────────┐
│   GUARDRAILS (Input)        │
│   • Prompt injection check  │
│   • Input sanitization      │
└─────────────────────────────┘
      │
      ▼
┌─────────────────────────────┐
│         CLAUDE              │
│   • System prompt           │
│   • Few-shot examples       │
│   • Chain-of-thought        │
└─────────────────────────────┘
      │
      ├──────────────┬────────────────┐
      ▼              ▼                ▼
┌──────────┐  ┌─────────────┐  ┌─────────────┐
│ Employee │  │ Policy RAG  │  │  Approval   │
│ Lookup   │  │ Search      │  │  Threshold  │
└──────────┘  └─────────────┘  └─────────────┘
      │
      ▼
┌─────────────────────────────┐
│   GUARDRAILS (Output)       │
│   • Schema validation       │
│   • Confidence threshold    │
└─────────────────────────────┘
      │
      ▼
{ "approved": bool, "reason": str, "policy_ref": str }
```

---

## Patterns Demonstrated

### 1. Prompt Engineering
- System prompt with role definition and constraints
- Few-shot examples for consistent reasoning
- Chain-of-thought prompting for explainable decisions

### 2. RAG (Retrieval Augmented Generation)
- Embedding-based policy retrieval
- Confidence scoring on retrieved chunks
- Context window management

### 3. Tool Use / MCP
- Standardized tool interfaces via MCP server
- Employee database lookup
- Policy search function
- Approval threshold checking

### 4. Guardrails
- Input validation and sanitization
- Prompt injection detection
- Output schema enforcement
- Confidence thresholds for human escalation

### 5. Evals
- Golden test cases with expected outcomes
- LLM-as-judge grading for nuanced responses
- Regression testing for prompt changes

---

## Project Structure

```
policy-enforcer/
├── README.md
├── requirements.txt
├── config.py                 # Configuration and constants
├── embeddings.py             # Vector embeddings and retrieval
├── mcp_server.py             # Tool definitions (MCP pattern)
├── guardrails.py             # Input/output validation
├── prompts.py                # System prompts and few-shot examples
├── agent.py                  # Main orchestration
├── evals/
│   ├── __init__.py
│   ├── test_cases.py         # Golden test cases
│   ├── run_evals.py          # Evaluation harness
│   └── grader.py             # LLM-as-judge implementation
├── data/
│   ├── policies.json         # Policy corpus
│   ├── employees.json        # Employee database
│   └── rules.json            # Approval rules
└── docs/
    └── ARCHITECTURE.md       # Detailed design decisions
```

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="your-key"

# Run the agent
python agent.py

# Run evaluations
python evals/run_evals.py
```

---

## Example Interaction

```
Employee: Can I book a business class flight to Tokyo for the client meeting?

Agent reasoning:
1. Looking up employee level... → Senior Consultant
2. Searching policies for "flight class international"...
3. Found: "Business class permitted for flights >6 hours for Senior+ levels"
4. Tokyo flight from US is ~13 hours ✓
5. Employee level is Senior ✓

Response:
{
  "approved": true,
  "reason": "Business class is permitted for international flights over 6 hours for Senior Consultant level and above.",
  "policy_ref": "travel-policy-4.2.1",
  "confidence": 0.95
}
```

---

## Design Decisions

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed documentation on:
- Why confidence thresholds matter for enterprise deployment
- How the guardrails layer prevents prompt injection
- Trade-offs in RAG chunk size and retrieval count
- The eval framework and why LLM-as-judge works here

---

## What This Isn't

This is a **demonstration prototype**, not production software. It shows the patterns, not a deployable product. In production you'd need:
- Real policy corpus and employee database
- Authentication and authorization
- Audit logging
- Human-in-the-loop for low-confidence decisions
- Monitoring and observability

---

## Built With

- Python 3.11+
- Anthropic Claude API
- Vector embeddings for RAG

---

## Author

Milorad Felbapov
[LinkedIn](https://linkedin.com/in/mfelbapov) | [GitHub](https://github.com/mfelbapov)
