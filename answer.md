# Forward Deployed Engineering: Building AI Solutions at the Customer Edge

*Presentation for Accenture Engineering Team*

---

## What is a Forward Deployed Engineer?

FDEs embed directly with strategic customers to drive transformational AI adoption. Unlike traditional consulting, FDEs:

- **Ship production code** within customer environments
- **Build reusable technical artifacts** (MCP servers, agents, skills)
- **Bridge the gap** between AI capabilities and real business problems
- **Operate autonomously** while representing their organization at the highest level

---

## Customer Scenarios

### Scenario 1: Financial Services - Trading Desk AI Assistant

**Context:** A global investment bank wants to augment their trading desk analysts with AI-powered research and reporting capabilities.

**Discovery Phase:**
- Shadowed traders to understand daily workflows
- Mapped data sources: Bloomberg terminals, internal research, news feeds, proprietary models
- Identified compliance requirements: audit trails, no hallucinated financial data, explainability

**Solution Delivered:**
- Claude-powered assistant for market analysis and report generation
- MCP server connecting to internal data warehouse with row-level security
- Custom evaluation framework measuring factual accuracy against source documents
- Human-in-the-loop review workflow for client-facing outputs

**Technical Challenges Solved:**
- Sub-second latency requirements for real-time market queries
- Structured output generation matching existing report templates
- Citation and source attribution for compliance

---

### Scenario 2: Healthcare - Clinical Documentation

**Context:** A hospital network wants to reduce physician documentation burden while maintaining accuracy and compliance.

**Discovery Phase:**
- Observed physician workflows across specialties (ED, primary care, surgery)
- Mapped EHR integration points (Epic/Cerner APIs)
- Documented HIPAA and clinical accuracy requirements

**Solution Delivered:**
- AI-assisted clinical note generation from audio transcripts
- MCP server integration with EHR for patient context retrieval
- Specialty-specific prompt templates (cardiology, oncology, pediatrics)
- Physician review interface with diff-based editing

**Technical Challenges Solved:**
- Medical terminology accuracy and ICD-10 code suggestions
- Patient data isolation and PHI handling
- Integration with existing clinical workflows without disruption

---

### Scenario 3: Enterprise - Knowledge Management

**Context:** A Fortune 500 company has knowledge scattered across SharePoint, Confluence, Slack, and tribal knowledge. Employees spend hours searching for information.

**Discovery Phase:**
- Catalogued knowledge repositories and access patterns
- Interviewed employees across departments about pain points
- Mapped organizational hierarchy and access control requirements

**Solution Delivered:**
- Multi-agent system for document search, summarization, and Q&A
- Sub-agents for: document retrieval, answer synthesis, source validation
- Role-based access control respecting existing permissions
- Analytics dashboard tracking usage patterns and knowledge gaps

**Technical Challenges Solved:**
- Unified search across heterogeneous data sources
- Source attribution and confidence scoring
- Handling stale/outdated information gracefully

---

## Technical Deliverables: What FDEs Build

### MCP Servers

MCP (Model Context Protocol) servers extend Claude's capabilities to interact with customer systems:

| MCP Server Type | Purpose | Example |
|-----------------|---------|---------|
| **Database Connector** | Secure query execution with schema awareness | `query_sales_data(region, date_range)` |
| **Document Retrieval** | Enterprise search integration | `search_confluence(query, space)` |
| **Workflow Automation** | Trigger downstream systems | `create_jira_ticket(summary, priority)` |
| **API Gateway** | Unified access to internal services | `call_pricing_api(product_id)` |

**Key Design Principles:**
- Minimal surface area (only expose what's needed)
- Strong typing and validation
- Comprehensive logging for debugging and audit
- Graceful degradation when services are unavailable

### Agent Skills

Skills are reusable capabilities that can be composed into larger workflows:

```
Skill: Financial Analysis
├── Parse earnings reports
├── Extract key metrics (revenue, EBITDA, guidance)
├── Compare against analyst consensus
└── Generate summary with bull/bear cases

Skill: Code Review
├── Analyze diff for security vulnerabilities
├── Check style guide compliance
├── Suggest performance optimizations
└── Generate review comments in PR format

Skill: Meeting Summarization
├── Extract action items with owners
├── Identify decisions made
├── Flag unresolved questions
└── Generate follow-up email draft
```

### Sub-Agents

Sub-agents handle specific tasks within a larger orchestration:

| Sub-Agent | Role | When to Use |
|-----------|------|-------------|
| **Validator** | Fact-check outputs against sources | High-stakes domains (legal, medical, financial) |
| **Transformer** | Convert between formats | Data normalization, report generation |
| **Router** | Classify and dispatch requests | Multi-domain systems |
| **Monitor** | Quality assurance and drift detection | Production systems requiring observability |

---

## Typical Engagement Workflow

### Phase 1: Discovery

**Activities:**
- Stakeholder interviews (business sponsors, end users, IT)
- Workflow mapping and pain point identification
- Data landscape assessment (sources, quality, access)
- Success criteria definition with measurable KPIs

**Outputs:**
- Requirements document with prioritized use cases
- Data access plan and security review
- Initial architecture proposal
- Go/no-go recommendation

---

### Phase 2: Prototype

**Activities:**
- Rapid proof-of-concept on highest-value use case
- Prompt engineering iteration with real data
- Initial evaluation framework setup
- Stakeholder demo and feedback collection

**Outputs:**
- Working prototype demonstrating core value
- Baseline accuracy/quality metrics
- Revised scope and success criteria
- Technical risk assessment

---

### Phase 3: Production Build

**Activities:**
- Enterprise integration (SSO, logging, monitoring)
- MCP server development and testing
- Agent orchestration implementation
- Comprehensive evaluation at scale
- Security review and penetration testing

**Outputs:**
- Production-ready application
- Deployment runbooks
- Monitoring dashboards
- Evaluation results and quality benchmarks

---

### Phase 4: Deployment & Handoff

**Activities:**
- Production rollout (phased or full)
- User training and documentation
- Knowledge transfer to customer engineering team
- Success metrics validation

**Outputs:**
- Live production system
- Operational documentation
- Training materials
- Engagement retrospective with lessons learned

---

## Key Success Metrics

### Technical Metrics

| Metric | What It Measures | Target Range |
|--------|------------------|--------------|
| **Task Accuracy** | Correctness of AI outputs | 90-99% (domain-dependent) |
| **Latency (P50/P99)** | Response time | <2s P50, <10s P99 |
| **Error Rate** | Failed requests | <1% |
| **Fallback Rate** | Human escalations | <5% |
| **Cost per Query** | API + infrastructure costs | Varies by use case |

### Business Metrics

| Metric | What It Measures | How to Calculate |
|--------|------------------|------------------|
| **Time Saved** | Productivity gain | Before/after time studies |
| **Adoption Rate** | User engagement | DAU/MAU vs. target population |
| **Quality Improvement** | Output quality vs. manual | Blind comparison studies |
| **ROI** | Return on investment | (Time saved * labor cost) / deployment cost |

### Engagement Metrics

| Metric | What It Measures | Why It Matters |
|--------|------------------|----------------|
| **Time to Prototype** | Discovery to working demo | Early value demonstration |
| **Time to Production** | Prototype to live system | Overall delivery velocity |
| **Patterns Contributed** | Reusable components created | Team learning and scale |
| **Expansion Opportunities** | New use cases identified | Customer relationship depth |

---

## Building Your FDE Team: Key Skills & Mindset

### Technical Depth + Customer Empathy
FDEs must write production code AND understand business context. The best FDEs can explain a complex technical tradeoff to a non-technical stakeholder.

### Comfort with Ambiguity
Enterprise environments are messy. Requirements change. Stakeholders disagree. FDEs thrive when the path isn't clear.

### Rapid Prototyping
Get something working in days, not months. Early demos build trust and accelerate feedback loops.

### Cross-Functional Collaboration
FDEs work with sales, product, engineering, and customer teams simultaneously. Low ego, high cooperation.

### Safety-First Mindset
AI systems can fail in unexpected ways. FDEs build guardrails, monitoring, and graceful degradation from day one.

---

## Questions?

---

*"You'll sit at the frontier of enterprise AI deployments... This is a significant responsibility: you'll play a key role in championing safe, beneficial AI in the enterprise."*
