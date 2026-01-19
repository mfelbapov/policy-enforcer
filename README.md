# Corporate Policy Enforcer

A production-ready AI system demonstrating FDE-level skills:
- **Prompt Engineering**: System prompts, few-shot examples, chain-of-thought
- **RAG**: Embedding-based retrieval with confidence thresholds
- **Tool Use / MCP**: Standardized tool interfaces
- **Evals**: Automated testing with LLM-as-judge
- **Guardrails**: Input validation, prompt injection defense, output validation
- **Streaming**: Real-time response streaming
- **Structured Output**: JSON schema enforcement

## The Problem

Employees ask: "Can I expense a first-class flight to London?"

The system must:
1. Identify the employee's role/level (Tool Use)
2. Retrieve relevant policy sections (RAG)
3. Reason through the policy (Prompt Engineering)
4. Return a compliant answer (Structured Output)
5. Never hallucinate or approve unauthorized expenses (Guardrails + Evals)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Question                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GUARDRAILS (Input)                           │
│  • Prompt injection detection                                   │
│  • Input sanitization                                           │
│  • Rate limiting                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         CLAUDE                                  │
│  • System prompt with few-shot examples                         │
│  • Chain-of-thought reasoning                                   │
│  • Tool selection                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│      TOOL: Employee DB    │    │      TOOL: Policy RAG    │
│  • get_employee_level     │    │  • search_policy         │
│  • validate permissions   │    │  • confidence scoring    │
└──────────────────────────┘    └──────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   GUARDRAILS (Output)                           │
│  • Response validation                                          │
│  • Structured output enforcement                                │
│  • Confidence thresholding                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Structured Response                          │
│  { "approved": bool, "reason": str, "policy_ref": str }         │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
policy-enforcer/
├── README.md
├── requirements.txt
├── config.py                 # Configuration and constants
├── embeddings.py             # RAG: Vector embeddings and retrieval
├── mcp_server.py             # MCP: Tool definitions
├── guardrails.py             # Input/output validation
├── prompts.py                # System prompts and few-shot examples
├── agent.py                  # Main orchestration loop
├── streaming.py              # Streaming response handler
├── evals/
│   ├── test_cases.py         # Golden test cases
│   ├── run_evals.py          # Evaluation harness
│   └── grader.py             # LLM-as-judge grader
└── data/
    └── policies.json         # Policy document corpus
```

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
