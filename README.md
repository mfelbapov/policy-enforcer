# Corporate Policy Enforcer

An AI agent that answers employee policy questions — it looks up who's asking, finds the relevant policy, reasons through the rules, and returns a structured decision.

**Example:** "Can I expense a first-class flight to London?"

---

## Why I Built This

I wanted to see what it takes to go beyond a basic LLM API call. So I picked a simple scenario — an employee asks if they can expense something — and built the full loop around it: RAG to pull the right policy, tool use to look up the employee and check approval rules, guardrails to block bad inputs and validate outputs, structured JSON so the response is actually usable, and evals to make sure it doesn't break when I change a prompt. Nothing here is production-ready, but it gave me a concrete way to explore how these pieces fit together in a hypothetical deployment.

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
│         LLM                 │
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

# Set API keys
export LLM_API_KEY="your-key"
export EMBEDDINGS_API_KEY="your-embeddings-key"  # optional — falls back to mock embeddings

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

## Built With

- Python 3.11+
- Any_Model_Api
- Any_Embeddings_Api embeddings for RAG
- FastMCP for tool interfaces
- Pydantic for validation and structured output

---

## Author

Milorad Felbapov
[LinkedIn](https://linkedin.com/in/mfelbapov) | [GitHub](https://github.com/mfelbapov)
