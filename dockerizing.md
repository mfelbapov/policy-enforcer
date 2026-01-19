# Dockerization Strategy for Policy Enforcer

## Application Overview

This is a Corporate Policy Enforcer - a Python-based AI system that answers employee policy questions using Claude AI with RAG (Retrieval-Augmented Generation) and safety guardrails.

---

## Recommended Container Architecture

### Container A: Main Application

**Contains:**
- `agent.py` - Main orchestration engine
- `guardrails.py` - Input/output validation
- `embeddings.py` - RAG implementation
- `prompts.py` - System prompts and few-shot examples
- `config.py` - Configuration
- `data/policies.json` - Policy corpus
- `requirements.txt` - Dependencies

**Why:**
- These components form a tightly coupled unit - the agent orchestrates guardrails, embeddings, and prompts in a single request/response cycle
- They share in-memory state (cached policy index)
- Network latency between these components would degrade performance
- This is the core runtime that serves user queries

**Environment Variables Needed:**
- `ANTHROPIC_API_KEY`
- `VOYAGE_API_KEY`

---

### Container B: MCP Server (Optional - for Claude Desktop integration)

**Contains:**
- `mcp_server.py` - FastMCP tool server
- `data/policies.json` - Policy corpus (shared)
- Minimal dependencies from `requirements.txt` (mcp, fastmcp, pydantic)

**Why:**
- The MCP server is a separate process that exposes tools via stdio/SSE for Claude Desktop
- It can run independently when the main agent isn't needed
- Different deployment model: stdio server vs. HTTP service
- Lighter resource footprint than the full application
- May not be needed in all deployments (only for Claude Desktop users)

**Note:** This container is only needed if you're using Claude Desktop integration. For API-only deployments, skip this container.

---

### Container C: Evaluation Runner

**Contains:**
- `evals/run_evals.py` - Test harness
- `evals/grader.py` - LLM-as-judge grader
- `evals/test_cases.py` - Test case definitions
- `agent.py` + dependencies (needs full agent to test)
- Full `requirements.txt`

**Why:**
- Evaluation is a batch job, not a persistent service
- Runs periodically in CI/CD pipelines, not on every request
- May need different resource limits (longer timeouts, more memory)
- Keeps test infrastructure isolated from production
- Can be run on-demand without affecting production containers
- Different lifecycle: runs to completion, then exits

**Environment Variables Needed:**
- `ANTHROPIC_API_KEY`
- `VOYAGE_API_KEY`

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     PRODUCTION                               │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           Container A: Main Application              │    │
│  │                                                      │    │
│  │   agent.py ─┬─► guardrails.py                       │    │
│  │             ├─► embeddings.py ──► Voyage AI API     │    │
│  │             └─► prompts.py                          │    │
│  │                    │                                │    │
│  │                    ▼                                │    │
│  │             Claude API (Anthropic)                  │    │
│  │                                                      │    │
│  │   Exposed: HTTP/CLI interface                       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │        Container B: MCP Server (Optional)            │    │
│  │                                                      │    │
│  │   mcp_server.py ──► stdio/SSE for Claude Desktop    │    │
│  │                                                      │    │
│  │   Exposed: stdio (for local) or SSE endpoint        │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                       CI/CD                                  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │          Container C: Evaluation Runner              │    │
│  │                                                      │    │
│  │   run_evals.py ──► agent.py ──► Claude API          │    │
│  │        │                                            │    │
│  │        ▼                                            │    │
│  │   grader.py ──► Claude Haiku (for grading)          │    │
│  │        │                                            │    │
│  │        ▼                                            │    │
│  │   JSON report output                                │    │
│  │                                                      │    │
│  │   Runs: On-demand / scheduled / PR checks           │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Why This Split?

### 1. Separation of Concerns
- **Runtime vs. Testing**: Production code (A, B) is separate from evaluation code (C)
- **Core vs. Integration**: Main app (A) vs. Claude Desktop integration (B)

### 2. Different Scaling Needs
- Container A scales with user traffic
- Container B is typically single-instance (local dev tool)
- Container C runs as batch jobs, scales with CI/CD parallelism

### 3. Different Resource Profiles
- Container A: Low latency, consistent memory
- Container B: Minimal resources, stdio-based
- Container C: Higher memory/timeout limits for batch processing

### 4. Deployment Flexibility
- Can deploy only Container A for API-only use cases
- Add Container B only if Claude Desktop integration is needed
- Container C lives in CI/CD pipeline, not production

---

## Alternative: Single Container (Simpler)

For simpler deployments, everything can run in one container:

**Single Container Contains:**
- All Python files
- `data/policies.json`
- `requirements.txt`

**When to use single container:**
- Small team / early stage
- No CI/CD pipeline yet
- Claude Desktop integration not needed
- Simpler infrastructure management

**Trade-offs:**
- Larger image size
- Can't scale components independently
- Test code ships with production code

---

## Summary

| Container | Purpose | When to Deploy |
|-----------|---------|----------------|
| A | Main Application | Always (core service) |
| B | MCP Server | Only if using Claude Desktop |
| C | Evaluation Runner | CI/CD pipeline only |

For most deployments, **Container A alone is sufficient**. Add B and C based on your specific needs.
