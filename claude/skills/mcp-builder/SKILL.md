---
name: mcp-builder
description: |
  Build MCP (Model Context Protocol) servers that extend Claude's capabilities. Use when:
  - User wants to create a new MCP server
  - Need to add tools/resources to an existing MCP server
  - Integrating external systems (APIs, databases, CLIs) with Claude
  - Building query tools for subagents to use
  - Need to understand MCP server patterns and best practices
  Reference implementation: /Users/michaelzakany/projects/proxmox/mcp-server
---

# Build MCP Servers

MCP servers extend Claude with custom tools and resources. This skill encodes patterns from a working production server.

## When to Build an MCP Server

Build an MCP server when you need to:
- Give Claude access to live system data (kubectl, APIs, databases)
- Provide domain-specific tools for subagents
- Expose resources that change over time
- Wrap complex CLI tools with structured output

## Project Structure

```
mcp-server/
├── package.json          # type: module, dependencies
├── tsconfig.json         # ES2022, NodeNext modules
├── src/
│   ├── index.ts          # Server setup, tool/resource registration
│   ├── tools/            # One file per tool
│   │   ├── list-services.ts
│   │   └── check-health.ts
│   ├── clients/          # External system wrappers
│   │   └── kubernetes.ts
│   └── resources/        # MCP resources (optional)
│       └── services.ts
└── dist/                 # Compiled output
```

## Quick Start

1. Initialize project:
```bash
mkdir my-mcp-server && cd my-mcp-server
npm init -y
npm pkg set type=module
npm install @modelcontextprotocol/sdk zod
npm install -D typescript @types/node
```

2. Create tsconfig.json:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true
  },
  "include": ["src/**/*"]
}
```

3. Create src/index.ts - see references/index-template.md

4. Build and test:
```bash
npm run build
node dist/index.js  # Should print server startup message
```

5. Add to .mcp.json:
```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["/absolute/path/to/dist/index.js"]
    }
  }
}
```

## Tool Design Principles

**Query tools** (for researcher/planner subagents):
- Return structured JSON data
- No side effects
- Include context for decision making

**Execution tools** (for executor subagent only):
- Perform actions (apply, create, delete)
- Support dry-run mode
- Require plan approval first

See references/tool-pattern.md for implementation details.

## Client Wrapper Pattern

Wrap external systems (kubectl, APIs) in typed client modules:
- Parse output into TypeScript interfaces
- Handle errors gracefully
- Timeout protection

See references/client-pattern.md for implementation details.

## Common Patterns

### Zod Schemas for Parameters
```typescript
import { z } from "zod";

export const myToolSchema = {
  name: z.string().describe("Name of the thing"),
  namespace: z.string().optional().describe("Optional namespace"),
};
```

### Tool Return Format
```typescript
return {
  content: [{
    type: "text",
    text: JSON.stringify(result, null, 2),
  }],
};
```

### ESM Import Gotcha
Always use ESM imports, never CommonJS require():
```typescript
// CORRECT
import { readFileSync } from "fs";

// WRONG - breaks template detection
const { readFileSync } = require("fs");
```

## Testing

```bash
# Build
npm run build

# Test with MCP Inspector
npx @modelcontextprotocol/inspector node dist/index.js

# Manual test
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | node dist/index.js
```

## Integration with Subagents

MCP tools are automatically available to subagents defined in `~/.claude/agents/`.

Tool naming convention: `mcp__<server-name>__<tool_name>`

Example: `mcp__proxmox-k8s__list_services`

## Reference Files

- **references/index-template.md** - Complete index.ts template
- **references/tool-pattern.md** - Tool implementation pattern
- **references/client-pattern.md** - Client wrapper pattern
