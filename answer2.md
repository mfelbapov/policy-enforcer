# How Realistic is This Demo? Comparing Policy Enforcer to Anthropic's FDE Job Description

## Executive Summary

**Realism Score: 9/10**

This Policy Enforcer application closely mirrors the technical deliverables expected from an Anthropic Forward Deployed Engineer. It implements MCP servers, agent tool use, RAG-based retrieval, production guardrails, and evaluation frameworks - all explicitly mentioned in the job description. For a demonstration, this represents authentic FDE-level work.

---

## What is a Forward Deployed Engineer?

Anthropic's FDE role sits at the intersection of software engineering and AI implementation. Unlike traditional consulting, FDEs:

- Embed directly with strategic customers to build production AI applications
- Deliver specific technical artifacts: **MCP servers, sub-agents, and agent skills**
- Operate autonomously in complex enterprise environments
- Maintain expertise in LLM capabilities, implementation patterns, and AI product development

The role requires 4+ years of technical customer-facing experience, production LLM experience (prompt engineering, agent development, evaluation frameworks), and strong Python skills.

---

## Requirements Mapping: Job Description vs. Implementation

| Job Description Requirement | How Policy Enforcer Implements It |
|-----------------------------|-----------------------------------|
| "Build production applications with Claude models" | Full Claude API integration with tool use orchestration loop, streaming responses, and proper state management |
| "Deliver MCP servers" | FastMCP server implementation with three enterprise tools and Pydantic input validation |
| "Deliver sub-agents and agent skills" | Policy search, employee lookup, and approval threshold tools that compose into a reasoning agent |
| "Production experience with LLMs" | Streaming for real-time feedback, iteration limits to prevent runaway agents, graceful error recovery |
| "Advanced prompt engineering" | Few-shot examples, chain-of-thought reasoning steps, structured JSON output enforcement |
| "Evaluation frameworks" | 20-case test suite, LLM-as-judge grading with Claude Haiku, systematic pass/fail tracking |
| "Deployment at scale" | Configuration management, async-ready architecture, confidence-based decision thresholds |
| "High standards for safety and reliability" | Multi-layer guardrails: prompt injection detection, schema validation, PII redaction, human escalation triggers |

---

## Technical Patterns That Reflect Real FDE Work

### 1. MCP Server Architecture

The job description explicitly lists "MCP servers" as a deliverable. This demo implements a FastMCP server with three tools following production patterns:

- **policy_get_employee_info** - Read-only, idempotent lookup with proper annotations
- **policy_search_manual** - Semantic search with confidence scoring and retrieval thresholds
- **policy_check_approval_threshold** - Deterministic business logic for approval routing

Each tool uses Pydantic models with field constraints, exactly how enterprise integrations are built.

### 2. RAG with "Refuse to Hallucinate"

The embedding system uses Voyage AI (chosen for enterprise/financial content quality) with a critical pattern: if retrieval confidence falls below 0.75, the system explicitly refuses to answer rather than guess. This "know what you don't know" pattern is essential for enterprise AI where wrong answers create compliance risk.

### 3. Guardrails as First-Class Citizens

Production FDE work requires defense-in-depth. This demo implements:

- **Input validation** - Length limits, encoding attack detection, pattern-based injection detection
- **Output validation** - JSON schema enforcement, confidence thresholding, semantic consistency checks
- **Escalation logic** - High-value transactions automatically route to human approval
- **PII handling** - Detection patterns for SSN, credit cards, and common sensitive data

### 4. Evaluation-Driven Development

The 20-test evaluation suite covers five categories (travel, expense, approval, edge cases, negative tests) with expected outputs. Using Claude Haiku as an LLM-as-judge for cost-effective grading is exactly how production evaluation pipelines work. The current 45% pass rate is realistic for early-stage development before iteration.

### 5. Tool Use Loop with Proper State

The agent orchestration follows the canonical pattern: send message with tools, parse tool_use blocks, execute tools, feed results back, repeat until end_turn. This isn't a simple API call - it's a stateful reasoning loop that mirrors how production agents operate.

---

## What Senior Engineers Will Recognize

**Architecture decisions that signal production experience:**

- Separation of concerns: prompts, guardrails, embeddings, and agent logic in separate modules
- Configuration externalized to environment variables with sensible defaults
- Streaming support for user experience (real-time feedback during processing)
- Max iteration limits to prevent infinite loops in tool use
- Confidence scoring throughout the pipeline, not just at the end

**Patterns borrowed from traditional enterprise development:**

- Pydantic for input validation (familiar to anyone who's built APIs)
- Structured logging approach (Rich library for console output)
- Test harness with mock support (can test without API calls)
- Clear error handling with fallback behaviors

---

## Honest Assessment: What's Missing for Full Production

| Gap | Why It's Acceptable for a Demo |
|-----|-------------------------------|
| No observability/tracing | Production would use LangSmith, Weights & Biases, or custom telemetry. Demo complexity trade-off. |
| Single model choice | Real FDE work often A/B tests Sonnet vs. Haiku for cost optimization. Demo focuses on patterns. |
| No customer data integration | Actual engagements connect to HRIS, ERP, or policy management systems. Demo uses mock data. |
| Limited policy corpus | Nine policies are enough to demonstrate RAG; production would have hundreds. |
| No authentication/authorization | Enterprise deployment would integrate with SSO and role-based access. Out of scope for demo. |

These gaps are expected. A demo that included full observability, multi-model routing, and enterprise SSO would take months and obscure the core patterns being demonstrated.

---

## Why This Matters for Accenture

This demo represents the type of engagement where:

1. **Discovery phase** - Understanding client policy structure, approval hierarchies, and compliance requirements
2. **Rapid prototyping** - Building a working system in weeks, not months
3. **Technical handoff** - Delivering artifacts the client's team can extend and maintain
4. **Pattern documentation** - Establishing guardrails and evaluation approaches for future AI work

The FDE model is about accelerating enterprise AI adoption through hands-on building, not just advisory. This demo shows what "hands-on" looks like in practice.

---

## Conclusion

This Policy Enforcer application would be appropriate to show during an Anthropic FDE interview or customer engagement. It demonstrates:

- Every technical artifact mentioned in the job description (MCP servers, agent skills, evaluation frameworks)
- Production-grade patterns (guardrails, confidence thresholding, streaming, state management)
- A real business problem that enterprises face (expense policy compliance at scale)
- Honest limitations (45% eval pass rate) that reflect actual development iteration

**For your presentation:** This is not a toy demo. It represents 2-3 weeks of focused FDE work building a production-ready foundation. The patterns here transfer directly to any Claude-powered enterprise application.

---

*Analysis prepared for Accenture internal presentation. Comparison based on Anthropic FDE job posting (Boston/NYC/Seattle/SF/DC locations, $200K-$300K OTE range).*
