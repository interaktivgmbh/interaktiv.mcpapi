# MCP for Websites: A Vision for LLM-Accessible Web Services

## Introduction

The Model Context Protocol (MCP) provides a standardized way for Large Language Models (LLMs) to interact with external tools and data sources. While MCP is currently primarily used in developer tools (Claude Code, Claude Desktop), there is potential for MCP to become a standard way for websites to expose functionality to LLMs.

This document outlines a vision for how websites could provide MCP endpoints alongside their traditional interfaces, enabling a new paradigm of LLM-driven web interactions.

## The Multi-Interface Website

Modern websites already serve multiple audiences through different interfaces:

| Interface | Audience | Purpose |
|-----------|----------|---------|
| HTML | Humans | Visual browsing |
| RSS/Atom | Feed readers | Content syndication |
| REST/GraphQL API | Applications | Programmatic access |
| `robots.txt` | Web crawlers | Crawl directives |
| `sitemap.xml` | Search engines | Content discovery |
| **MCP endpoint** | **LLMs** | **Tool-based interaction** |

MCP would be the interface optimized for LLM consumption - not just data retrieval, but actionable tools that an LLM can reason about and use on behalf of users.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Website (e.g., Plone CMS)                                      │
│                                                                 │
│  Human Interface                                                │
│  ├── /                         Homepage                         │
│  ├── /news/                    News section                     │
│  └── /contact                  Contact form                     │
│                                                                 │
│  Machine Interfaces                                             │
│  ├── /api/                     REST API                         │
│  ├── /sitemap.xml              Search engine sitemap            │
│  ├── /@mcp                     MCP endpoint for LLMs            │
│  └── /.well-known/mcp.json     MCP discovery (proposed)         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Use Case Scenario

### The User Journey

1. **User** opens an LLM chat interface (Claude, Gemini, ChatGPT, etc.)
2. **User** asks: "Calculate my solar panel savings using the calculator on example-energy.com"
3. **LLM** discovers the website's MCP endpoint via `/.well-known/mcp.json`
4. **LLM** queries available tools, finds `calculate_solar_savings`
5. **LLM** asks user for required inputs (location, roof size, energy usage)
6. **LLM** calls the tool with parameters
7. **LLM** presents results in conversational format

### Data Flow

```
┌──────────┐     ┌──────────────┐     ┌─────────────────┐
│   User   │────►│ LLM Provider │────►│ Website MCP     │
│ Browser  │◄────│   Backend    │◄────│ Endpoint        │
└──────────┘     └──────────────┘     └─────────────────┘
    chat           tool calls           JSON-RPC 2.0
```

Note: The LLM provider's backend makes the MCP calls, not the user's browser. This avoids CORS issues entirely.

## MCP Endpoint Design Principles

### 1. Tool Granularity

Tools should be **atomic and focused**, not monolithic:

```
Good:
- search_products(query, category, price_range)
- get_product_details(product_id)
- check_availability(product_id, location)

Bad:
- do_everything(action, params)
```

### 2. Self-Documenting

Tools should have clear descriptions that help LLMs understand when and how to use them:

```json
{
  "name": "calculate_mortgage",
  "description": "Calculate monthly mortgage payments. Use this when users ask about home loan costs, mortgage affordability, or monthly payments for a house purchase.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "principal": {
        "type": "number",
        "description": "Loan amount in USD"
      },
      "interest_rate": {
        "type": "number",
        "description": "Annual interest rate as percentage (e.g., 6.5 for 6.5%)"
      },
      "term_years": {
        "type": "integer",
        "description": "Loan term in years (typically 15 or 30)"
      }
    },
    "required": ["principal", "interest_rate", "term_years"]
  }
}
```

### 3. Permission-Aware

Different tools may require different access levels:

| Permission Level | Example Tools |
|-----------------|---------------|
| Anonymous | `search`, `get_public_content`, `calculate` |
| Authenticated | `get_user_profile`, `list_orders` |
| Privileged | `create_content`, `modify_settings` |

### 4. LLM-Optimized Responses

Return data structured for LLM comprehension, not just raw database output:

```json
{
  "result": {
    "monthly_payment": 1264.14,
    "total_interest": 155090.40,
    "total_cost": 455090.40,
    "summary": "For a $300,000 loan at 6.5% over 30 years, your monthly payment would be $1,264.14"
  }
}
```

## Discovery Mechanism (Proposed)

### Well-Known Endpoint

Websites could advertise MCP support via `/.well-known/mcp.json`:

```json
{
  "mcp_version": "2024-11-05",
  "endpoint": "https://example.com/@mcp",
  "transport": "http",
  "authentication": {
    "anonymous": true,
    "methods": ["bearer", "basic"]
  },
  "tools_summary": [
    "search - Search website content",
    "calculate_savings - Calculate potential savings",
    "get_locations - Find nearby locations"
  ],
  "rate_limits": {
    "anonymous": "100/hour",
    "authenticated": "1000/hour"
  },
  "contact": "api@example.com"
}
```

### DNS-Based Discovery (Alternative)

```
_mcp.example.com TXT "endpoint=https://example.com/@mcp"
```

## Security Considerations

### For Website Operators

1. **Rate Limiting** - Prevent abuse from automated LLM calls
2. **Input Validation** - Never trust LLM-provided parameters
3. **Principle of Least Privilege** - Anonymous tools should only access public data
4. **Audit Logging** - Track tool usage for security analysis
5. **Cost Control** - If tools call paid APIs, implement usage limits

### For LLM Providers

1. **Tool Verification** - How to trust arbitrary MCP endpoints?
2. **User Consent** - Should users approve each new MCP server?
3. **Data Privacy** - What data flows through the LLM provider?
4. **Sandboxing** - Isolate tool execution from other operations

### Trust Model (Open Question)

How should LLM providers verify MCP endpoints?

| Approach | Pros | Cons |
|----------|------|------|
| Allow-list | High trust | Limited ecosystem |
| User approval | User control | UX friction |
| Domain verification | Proves ownership | Doesn't prove safety |
| Code signing | Verifiable | Complex infrastructure |
| Reputation system | Community-driven | Cold start problem |

## Current Ecosystem Status (December 2024)

| Component | Status |
|-----------|--------|
| MCP Protocol Specification | ✅ Stable (Anthropic) |
| Server SDKs (Python, TypeScript) | ✅ Available |
| Claude Desktop MCP support | ✅ Available |
| Claude Code CLI MCP support | ✅ Available |
| Browser-based Claude + custom MCP | ❌ Not available |
| ChatGPT MCP support | ❌ Not available |
| Gemini MCP support | ❌ Not available |
| Discovery standard | ❌ Not defined |
| Trust/verification model | ❌ Not defined |

## Roadmap Speculation

### Near Term (2025)
- More LLM providers adopt MCP or similar protocols
- Desktop/CLI tools mature with better MCP management
- Community proposals for discovery standards

### Medium Term (2025-2026)
- Browser-based LLMs allow user-added MCP servers
- Discovery standards emerge (`.well-known/mcp.json` or similar)
- Trust frameworks develop

### Long Term (2026+)
- MCP becomes as common as REST APIs
- Websites routinely expose MCP endpoints
- LLM agents autonomously discover and use web services

## Implementation: interaktiv.mcpapi for Plone

This Plone add-on implements an MCP endpoint, positioning Plone sites for this future:

### Current Features
- JSON-RPC 2.0 MCP endpoint at `/@mcp`
- Extensible tool system via Zope adapters
- Permission-aware tool filtering
- Anonymous access support

### Example Tool Registration

```python
# tools/calculator.py
from interaktiv.mcpapi.tools.base import MCPToolBase

class SolarCalculatorTool(MCPToolBase):
    name = 'calculate_solar_savings'
    description = 'Calculate potential savings from solar panel installation'
    schema = {
        'type': 'object',
        'properties': {
            'roof_sqm': {'type': 'number', 'description': 'Roof area in square meters'},
            'kwh_monthly': {'type': 'number', 'description': 'Current monthly electricity usage in kWh'},
            'location': {'type': 'string', 'description': 'City or postal code'}
        },
        'required': ['roof_sqm', 'kwh_monthly']
    }
    permission = 'zope2.View'

    def execute(self, params):
        # Calculation logic here
        savings = calculate_savings(params)
        return {
            'annual_savings_eur': savings,
            'summary': f'You could save approximately €{savings} per year with solar panels.'
        }
```

```xml
<!-- tools/configure.zcml -->
<adapter
    factory=".calculator.SolarCalculatorTool"
    provides="interaktiv.mcpapi.interfaces.IMCPTool"
    for="* zope.publisher.interfaces.browser.IDefaultBrowserLayer"
    name="calculate_solar_savings"
/>
```

## Conclusion

MCP has the potential to become the standard interface between LLMs and web services. While the ecosystem is still maturing, forward-thinking website operators can begin implementing MCP endpoints now to be ready when LLM providers enable broader MCP connectivity.

The key insight is that **MCP is not just another API** - it's an interface specifically designed for LLM reasoning and tool use. Just as websites adapted to serve mobile users, search engines, and API consumers, they will adapt to serve LLMs. MCP provides a protocol for that adaptation.

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [MCP GitHub Repository](https://github.com/modelcontextprotocol)
- [Anthropic MCP Announcement](https://www.anthropic.com/news/model-context-protocol)
