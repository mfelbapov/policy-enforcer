# Architecture & Design Decisions

This document explains the reasoning behind key design choices in the Policy Enforcer.

---

## Why These Patterns Matter

Enterprise AI deployment isn't about raw model capability — it's about building systems that are **reliable**, **auditable**, and **safe**. A model that's right 95% of the time but wrong unpredictably is worse than useless in a compliance context.

---

## Guardrails: Defense in Depth

### Input Validation

Before the query reaches the model:

1. **Sanitization** — Strip control characters, normalize whitespace
2. **Length limits** — Reject absurdly long inputs
3. **Prompt injection detection** — Pattern matching for common attacks

```python
INJECTION_PATTERNS = [
    r"ignore.*previous.*instructions",
    r"disregard.*above",
    r"you are now",
    r"new instructions:",
    r"system prompt:",
]
```

This isn't foolproof. Sophisticated attacks can evade pattern matching. But it catches the obvious attempts and raises the bar.

### Output Validation

After the model responds:

1. **Schema enforcement** — Response must match expected JSON structure
2. **Required fields** — `approved`, `reason`, `policy_ref` must all be present
3. **Confidence thresholds** — Low confidence triggers human review

```python
class PolicyDecision(BaseModel):
    approved: bool
    reason: str
    policy_ref: str
    confidence: float = Field(ge=0.0, le=1.0)
```

---

## RAG: Retrieval Strategy

### Why RAG?

Policies change. Fine-tuning a model every time the travel policy updates isn't practical. RAG lets us:
- Update policies without retraining
- Cite specific policy sections (auditability)
- Control what context the model sees

### Chunk Size Trade-offs

| Chunk Size | Pros | Cons |
|------------|------|------|
| Small (100-200 tokens) | Precise retrieval | May miss context |
| Medium (300-500 tokens) | Good balance | Standard choice |
| Large (500-1000 tokens) | Full context | May dilute relevance |

We use ~400 token chunks with 50 token overlap. This preserves paragraph-level context while keeping retrieval focused.

### Confidence Scoring

Not all retrieved chunks are equally relevant. We score each chunk and only include those above a threshold:

```python
def retrieve_policies(query: str, threshold: float = 0.7) -> list[Chunk]:
    chunks = vector_search(query, top_k=10)
    return [c for c in chunks if c.score >= threshold]
```

If no chunks meet the threshold, the system returns "insufficient information" rather than hallucinating.

---

## Tool Use: MCP Pattern

Tools are defined with clear schemas so the model knows what's available and how to use it:

```python
tools = [
    {
        "name": "get_employee_level",
        "description": "Look up an employee's level and department",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "string"}
            },
            "required": ["employee_id"]
        }
    },
    {
        "name": "search_policy",
        "description": "Search company policies for relevant sections",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    }
]
```

The model decides when to call tools based on the question. "Can I expense lunch?" might not need employee lookup. "Can I book first class?" does.

---

## Evals: LLM-as-Judge

### Why Not Just String Matching?

Policy responses are nuanced. Two valid answers might be worded differently:

- "Yes, this is permitted under section 4.2"
- "Business class is allowed for your level on international flights"

Both are correct. String matching would fail.

### The Grader Prompt

```python
GRADER_PROMPT = """
You are evaluating a policy enforcement response.

Expected outcome: {expected}
Actual response: {actual}

Grade on:
1. Correctness — Is the approval/denial decision correct?
2. Reasoning — Is the explanation accurate and complete?
3. Policy reference — Is the right policy section cited?

Return: PASS or FAIL with explanation.
"""
```

---

## What's Not Here (Production Requirements)

This prototype demonstrates patterns. Production would need:

- **Authentication** — Who is asking?
- **Audit logging** — Every decision recorded
- **Human escalation** — Low confidence → manager review
- **Monitoring** — Track accuracy, latency, cost
- **Versioning** — Policy updates don't break existing decisions
- **Rate limiting** — Prevent abuse

---

## References

- [Anthropic Claude Documentation](https://docs.anthropic.com)
- [RAG Best Practices](https://docs.anthropic.com/en/docs/build-with-claude/retrieval-augmented-generation)
- [Tool Use Guide](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
