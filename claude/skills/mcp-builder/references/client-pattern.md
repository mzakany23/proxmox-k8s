# MCP Client Wrapper Pattern

Client modules wrap external systems (CLI tools, APIs) with typed interfaces.

## File Structure

`src/clients/my-client.ts`

## CLI Wrapper Example (kubectl pattern)

```typescript
/**
 * Kubernetes client wrapper
 *
 * Executes kubectl commands and parses output
 */

import { execSync } from "child_process";

// Type definitions for parsed output
export interface PodInfo {
  name: string;
  namespace: string;
  status: string;
  ready: string;
  restarts: number;
  age: string;
}

export interface ServiceInfo {
  name: string;
  namespace: string;
  type: string;
  clusterIP: string;
  ports: string;
}

/**
 * Execute kubectl command with timeout
 */
export function kubectl(args: string, options?: { json?: boolean }): string {
  try {
    const cmd = options?.json ? `kubectl ${args} -o json` : `kubectl ${args}`;
    return execSync(cmd, {
      encoding: "utf-8",
      timeout: 30000,  // 30 second timeout
      stdio: ["pipe", "pipe", "pipe"],
    }).trim();
  } catch (error: any) {
    throw new Error(`kubectl ${args} failed: ${error.message}`);
  }
}

/**
 * Get pods - parse tabular output
 */
export function getPods(namespace?: string): PodInfo[] {
  const ns = namespace ? `-n ${namespace}` : "-A";
  const output = kubectl(`get pods ${ns} --no-headers`);

  if (!output) return [];

  return output.split("\n").map((line) => {
    const parts = line.trim().split(/\s+/);
    if (namespace) {
      const [name, ready, status, restarts, age] = parts;
      return { name, namespace, ready, status, restarts: parseInt(restarts) || 0, age };
    } else {
      const [ns, name, ready, status, restarts, age] = parts;
      return { name, namespace: ns, ready, status, restarts: parseInt(restarts) || 0, age };
    }
  });
}

/**
 * Check if resource exists
 */
export function resourceExists(resource: string, name: string, namespace: string): boolean {
  try {
    kubectl(`get ${resource} ${name} -n ${namespace}`);
    return true;
  } catch {
    return false;
  }
}
```

## API Client Example

```typescript
/**
 * External API client
 */

import { execSync } from "child_process";

export interface ApiResponse<T> {
  data: T;
  error?: string;
}

/**
 * Make HTTP request using curl (avoids dependency on fetch polyfill)
 */
export function apiCall<T>(
  method: string,
  url: string,
  body?: object,
  headers?: Record<string, string>
): ApiResponse<T> {
  try {
    const headerArgs = Object.entries(headers || {})
      .map(([k, v]) => `-H "${k}: ${v}"`)
      .join(" ");

    const bodyArg = body ? `-d '${JSON.stringify(body)}'` : "";

    const cmd = `curl -s -X ${method} ${headerArgs} ${bodyArg} "${url}"`;
    const output = execSync(cmd, {
      encoding: "utf-8",
      timeout: 30000,
    });

    return { data: JSON.parse(output) };
  } catch (error: any) {
    return { data: null as T, error: error.message };
  }
}
```

## File/Registry Client Example

```typescript
/**
 * Registry client - reads local JSON files
 */

import { readFileSync, existsSync, readdirSync } from "fs";
import { join } from "path";

const REGISTRY_PATH = "/path/to/registry";

export interface AppEntry {
  name: string;
  namespace: string;
  type: string;
  url?: string;
}

export interface Registry {
  apps: AppEntry[];
}

/**
 * Read registry file
 */
export function readRegistry(): Registry {
  const filePath = join(REGISTRY_PATH, "apps.json");

  if (!existsSync(filePath)) {
    return { apps: [] };
  }

  const content = readFileSync(filePath, "utf-8");
  return JSON.parse(content);
}

/**
 * List templates in directory
 */
export function listTemplates(): string[] {
  const templatesDir = join(REGISTRY_PATH, "templates");

  if (!existsSync(templatesDir)) {
    return [];
  }

  return readdirSync(templatesDir, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name);
}
```

## Key Patterns

1. **Typed interfaces** - Define types for all parsed data
2. **Error handling** - Catch and wrap errors with context
3. **Timeouts** - Always set timeouts for external calls
4. **Graceful fallbacks** - Return empty arrays/objects on failure
5. **ESM imports** - Use `import` not `require`
