# MCP Tool Implementation Pattern

## File Structure

Each tool in its own file: `src/tools/my-tool.ts`

## Complete Example

```typescript
/**
 * my_tool
 *
 * Brief description of what this tool does
 */

import { z } from "zod";
import { myClient } from "../clients/my-client.js";

// Schema defines parameters Claude sees
export const myToolSchema = {
  name: z.string().describe("Name to look up"),
  namespace: z.string().optional().describe("Namespace (default: default)"),
  includeDetails: z.boolean().optional().describe("Include extra details"),
};

// Handler function
export async function myTool(params: {
  name: string;
  namespace?: string;
  includeDetails?: boolean;
}): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const { name, namespace = "default", includeDetails = false } = params;

  // Use client to get data
  const data = myClient.getData(name, namespace);

  // Build result
  const result = {
    name,
    namespace,
    data,
    ...(includeDetails && { details: myClient.getDetails(name) }),
  };

  // Return in MCP format
  return {
    content: [{
      type: "text",
      text: JSON.stringify(result, null, 2),
    }],
  };
}
```

## Query Tool Pattern

For tools that return information:

```typescript
export async function listItems(params: {
  filter?: string;
}): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const items = getItems(params.filter);

  const summary = {
    total: items.length,
    items: items.map(i => ({
      name: i.name,
      status: i.status,
    })),
  };

  return {
    content: [{
      type: "text",
      text: JSON.stringify(summary, null, 2),
    }],
  };
}
```

## Execution Tool Pattern

For tools that perform actions:

```typescript
export const applySchema = {
  manifest: z.string().describe("YAML manifest to apply"),
  dryRun: z.boolean().optional().describe("Validate only, don't apply"),
};

export async function applyManifest(params: {
  manifest: string;
  dryRun?: boolean;
}): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const { manifest, dryRun = false } = params;

  if (dryRun) {
    const validation = validateManifest(manifest);
    return {
      content: [{
        type: "text",
        text: JSON.stringify({ dryRun: true, valid: validation.valid, errors: validation.errors }, null, 2),
      }],
    };
  }

  const result = executeApply(manifest);
  return {
    content: [{
      type: "text",
      text: JSON.stringify({ applied: true, result }, null, 2),
    }],
  };
}
```

## Health Check Pattern

For comprehensive status checks:

```typescript
interface Check {
  check: string;
  status: "pass" | "fail" | "warn" | "skip";
  details: string;
}

export async function checkHealth(params: {
  name: string;
}): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const checks: Check[] = [];

  // Run multiple checks
  try {
    const podStatus = getPodStatus(params.name);
    checks.push({
      check: "Pods",
      status: podStatus.healthy ? "pass" : "fail",
      details: podStatus.message,
    });
  } catch (error: any) {
    checks.push({
      check: "Pods",
      status: "fail",
      details: error.message,
    });
  }

  // Summarize
  const passed = checks.filter(c => c.status === "pass").length;
  const total = checks.filter(c => c.status !== "skip").length;
  const overall = checks.some(c => c.status === "fail") ? "FAIL" : "PASS";

  return {
    content: [{
      type: "text",
      text: JSON.stringify({
        name: params.name,
        overall,
        summary: `${passed}/${total} checks passed`,
        checks,
      }, null, 2),
    }],
  };
}
```

## Zod Schema Tips

```typescript
// Required string
name: z.string().describe("The name")

// Optional with default in handler
namespace: z.string().optional().describe("Namespace (default: apps)")

// Boolean flag
verbose: z.boolean().optional().describe("Show verbose output")

// Enum
capability: z.enum(["database", "cache", "queue"]).describe("Capability type")

// Array
tags: z.array(z.string()).optional().describe("Filter by tags")
```
