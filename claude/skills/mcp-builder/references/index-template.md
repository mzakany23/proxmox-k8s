# MCP Server Index Template

Complete template for src/index.ts:

```typescript
#!/usr/bin/env node
/**
 * My MCP Server
 *
 * Description of what this server provides.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

// Import tools
import { myTool, myToolSchema } from "./tools/my-tool.js";

// Create server instance
const server = new McpServer({
  name: "my-server",
  version: "1.0.0",
});

// Register tools
server.tool(
  "my_tool",
  "Description shown to Claude when selecting tools",
  myToolSchema,
  myTool
);

// Optional: Register resources
server.resource(
  "data://inventory",
  "Description of this resource",
  async () => {
    const content = await getInventory();
    return {
      contents: [{
        uri: "data://inventory",
        mimeType: "application/json",
        text: content,
      }],
    };
  }
);

// Server startup
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("My MCP server running on stdio");
  console.error("Tools: my_tool");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
```

## Key Points

1. **Shebang** - `#!/usr/bin/env node` for direct execution
2. **ESM imports** - Use `.js` extension even for `.ts` files (NodeNext resolution)
3. **console.error** - For startup messages (stdout is for MCP protocol)
4. **Tool registration** - name, description, schema, handler
