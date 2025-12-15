# MCP Current State and Availability

## Overview

This document provides a realistic assessment of MCP (Model Context Protocol) availability and practical considerations as of December 2025.

**Major Update:** MCP has evolved from an Anthropic-only protocol to an industry standard. In March 2025, OpenAI adopted MCP, and in December 2025, Anthropic donated MCP to the Agentic AI Foundation (AAIF) under the Linux Foundation.

## Agentic AI Foundation (AAIF)

On December 9, 2025, the Linux Foundation announced the formation of the Agentic AI Foundation (AAIF), with MCP as one of its founding projects alongside Block's "goose" and OpenAI's "AGENTS.md".

### Founding Projects
- **MCP (Model Context Protocol)** - Universal standard for connecting AI models to tools, data and applications
- **goose** - Open source, local-first AI agent framework by Block
- **AGENTS.md** - Universal standard for project-specific AI agent guidance by OpenAI

### Membership

**Platinum Members:**
Amazon, Anthropic, Block, Bloomberg, Cloudflare, Google, Microsoft, OpenAI

**Gold Members:**
Adyen, Cisco, Datadog, Docker, IBM, JetBrains, Okta, Oracle, Runlayer, SAP, Snowflake, Temporal, Tetrate, Twilio

**Silver Members:**
Chronosphere, Cosmonic, Elasticsearch, Hugging Face, Kubermatic, Pydantic, Spectro Cloud, SUSE, Uber, WorkOS, ZED

### MCP Adoption
MCP now has **10,000+ published servers** covering everything from developer tools to Fortune 500 deployments.

## MCP Client Availability

| Client | MCP Support | User Base | Notes |
|--------|-------------|-----------|-------|
| Claude Code CLI | Yes | Developers | Full MCP support via `claude mcp add` |
| Claude Desktop | Yes | Developers | Full MCP support |
| claude.ai (browser) | No | Mass market | No custom MCP support yet |
| ChatGPT Desktop | Yes | Developers | Developer mode beta |
| ChatGPT (browser) | Yes | Pro/Plus users | Settings → Connectors → Advanced → Developer mode |
| OpenAI Agents SDK | Yes | Developers | Full MCP support |
| OpenAI Codex CLI/IDE | Yes | Developers | Full MCP support |
| Gemini (browser) | No | Mass market | No MCP support |

**Key Insight:** MCP support has expanded significantly. ChatGPT Pro/Plus users can now use custom MCP servers directly in the browser, making MCP accessible beyond just developer tools.

## Tool Integration Models: Comparing Leading LLM Providers

The landscape has shifted significantly with OpenAI's adoption of MCP:

### Anthropic (Claude)
- **Model:** MCP (Model Context Protocol) - open protocol
- **Custom Tools:** Yes, in CLI and Desktop environments
- **Openness:** Open - any developer can create MCP servers
- **Limitation:** Not yet available in browser-based claude.ai

### OpenAI (ChatGPT)
- **Model:** MCP (adopted March 2025)
- **Custom Tools:** Yes - full MCP support
- **Openness:** Open - any MCP server can be connected
- **Availability:** ChatGPT browser (Pro/Plus with Developer mode), Desktop, Agents SDK, Codex
- **How to enable:** Settings → Connectors → Advanced → Developer mode

### Google (Gemini)
- **Model:** Apps - hand-picked partnerships
- **Custom Tools:** No - only pre-approved partners (e.g., GitHub)
- **Openness:** Most restrictive - closed ecosystem
- **Limitation:** No path for custom integrations without Google partnership
- **Note:** Google is a supporter of AAIF, so MCP support may come in the future

### Openness Spectrum (Updated)

```
More Open                                              More Closed
    |                                                        |
    v                                                        v
MCP (Anthropic + OpenAI)                              Gemini Apps
   (any server)                                   (hand-picked partners)
```

### Implications for Custom Integrations

| Provider | Can You Integrate? | How? |
|----------|-------------------|------|
| Anthropic | Yes | Create MCP server, use with CLI/Desktop |
| OpenAI | Yes | Create MCP server, enable Developer mode in ChatGPT |
| Google | Not yet | No current path, but may adopt MCP as AAIF supporter |

**Conclusion:** MCP is now the industry standard for LLM tool integration. With OpenAI's adoption, custom MCP servers can reach a much broader audience including ChatGPT Pro/Plus users in the browser.

## Practical Use Cases Today

### 1. Developer Tooling
Developers using Claude Code CLI can connect to the Plone MCP endpoint for:
- Searching content during development
- Querying site structure
- Debugging content issues

### 2. Internal Automation
Server-side scripts or autonomous agents can use MCP to:
- Automate content operations
- Build integrations between systems
- Create monitoring/reporting tools

### 3. End User Access (ChatGPT Pro/Plus)
ChatGPT Pro/Plus users can connect to your MCP endpoint:
- Enable Developer mode in ChatGPT settings
- Connect to your public MCP endpoint
- Use your Plone tools directly in ChatGPT conversations

## Alternatives for Broader Access

MCP now covers most use cases, but for users without ChatGPT Pro/Plus or Claude Desktop:

### REST API
- **Pros:** Universal compatibility, any HTTP client can use it
- **Cons:** Not optimized for LLM consumption, requires custom integration

### Custom Chat UI on Your Site
- **Pros:** Full control over UX, accessible to any visitor (including free-tier users), can use any LLM API
- **Cons:** Development effort required, ongoing API costs, need to host and maintain
- **Note:** Can reuse tool logic from MCP implementation

### Browser Extension
- **Pros:** Could inject MCP capabilities into existing LLM interfaces
- **Cons:** Complex to build, security concerns, requires user installation

## Comparison Matrix

| Approach | Reach | Effort | Control | Cost |
|----------|-------|--------|---------|------|
| MCP (ChatGPT + Claude) | High (Pro/Plus users) | Low | High | Low |
| REST API | Medium | Medium | High | Low |
| Custom Chat UI | High (all users) | High | High | High |
| Browser Extension | Medium | High | Medium | Low |

## Recommendations

### Immediate
- **Deploy your MCP endpoint publicly** - ChatGPT Pro/Plus users can connect to it now
- Ensure CORS headers are configured if needed for browser-based access
- Consider authentication requirements for public endpoints

### Short Term
- Add more tools to your MCP server (content retrieval, navigation, etc.)
- Document your MCP endpoint for users (how to connect from ChatGPT)
- Monitor usage and implement rate limiting if needed

### Medium Term
- Watch for claude.ai browser support for custom MCP
- Watch for Gemini MCP adoption (Google is AAIF supporter)
- Consider building complementary chat UI for users without Pro/Plus subscriptions

## Timeline (Actual Events)

| Date | Development |
|------|-------------|
| Nov 2024 | Anthropic releases MCP specification |
| Mar 2025 | OpenAI adopts MCP across products |
| Oct 2025 | ChatGPT Developer mode with full MCP support |
| Nov 2025 | MCP 1-year anniversary, spec update |
| Dec 2025 | MCP donated to AAIF (Linux Foundation) |

## Conclusion

MCP has become the industry standard for LLM tool integration. For `interaktiv.mcpapi`, this means:

1. **Immediate value** - ChatGPT Pro/Plus users can connect to your Plone MCP endpoint today
2. **Growing reach** - As more providers adopt MCP, your tools become accessible to more users
3. **Future-proof** - MCP is now governed by Linux Foundation with major industry backing

The investment in MCP infrastructure pays off now, not just in the future.

## References

### AAIF Formation (December 2025)
- [Anthropic: Donating the Model Context Protocol and establishing the Agentic AI Foundation](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)
- [Linux Foundation: Announces the Formation of the Agentic AI Foundation (AAIF)](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)
- [MCP Blog: MCP joins the Agentic AI Foundation](http://blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation/)
- [TechCrunch: OpenAI, Anthropic, and Block join new Linux Foundation effort](https://techcrunch.com/2025/12/09/openai-anthropic-and-block-join-new-linux-foundation-effort-to-standardize-the-ai-agent-era/)
- [GitHub Blog: MCP joins the Linux Foundation](https://github.blog/open-source/maintainers/mcp-joins-the-linux-foundation-what-this-means-for-developers-building-the-next-era-of-ai-tools-and-agents/)

### OpenAI MCP Adoption (March-October 2025)
- [OpenAI adopts rival Anthropic's standard for connecting AI models to data | TechCrunch](https://techcrunch.com/2025/03/26/openai-adopts-rival-anthropics-standard-for-connecting-ai-models-to-data/)
- [OpenAI Adds Full MCP Support to ChatGPT Developer Mode - InfoQ](https://www.infoq.com/news/2025/10/chat-gpt-mcp/)

### MCP Development
- [One Year of MCP: November 2025 Spec Release | Model Context Protocol Blog](https://blog.modelcontextprotocol.io/posts/2025-11-25-first-mcp-anniversary/)
- [MCP Apps: Extending servers with interactive user interfaces | Model Context Protocol Blog](http://blog.modelcontextprotocol.io/posts/2025-11-21-mcp-apps/)
- [Model Context Protocol - Wikipedia](https://en.wikipedia.org/wiki/Model_Context_Protocol)
