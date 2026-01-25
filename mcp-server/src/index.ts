#!/usr/bin/env node
/**
 * Proxmox K8s MCP Server
 *
 * An information-focused MCP server for Kubernetes homelab infrastructure.
 * Provides facts, options, and questions - not prescriptive commands.
 * Designed to work with the subagent chain: researcher → planner → executor → validator
 *
 * Query Tools (for researcher/planner):
 * - list_services: What's deployed in the cluster
 * - get_service_info: Detailed info about a specific service
 * - check_health: Health status of a service
 * - get_capability_options: Options for adding a capability (database, cache, etc.)
 * - get_deployment_pattern: Pattern info for an app type
 * - get_deployment_steps: Steps needed to deploy an app
 *
 * Execution Tools (for executor only, after plan approval):
 * - apply_manifest: Apply a Kubernetes manifest
 *
 * Resources:
 * - services://inventory: All deployed services with status
 * - templates://catalog: Available deployment templates
 * - architecture://overview: Architecture documentation from CLAUDE.md
 *
 * Transport:
 * - stdio (default): Standard I/O for local CLI usage
 * - streamable-http: HTTP transport for K8s deployment
 *   Set MCP_TRANSPORT=streamable-http and PORT=8000
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import express from "express";

// Query tool implementations
import { listServices, listServicesSchema } from "./tools/list-services.js";
import { getServiceInfo, getServiceInfoSchema } from "./tools/get-service-info.js";
import { checkHealth, checkHealthSchema } from "./tools/check-health.js";
import { getCapabilityOptions, getCapabilityOptionsSchema } from "./tools/get-capability-options.js";
import { getDeploymentPattern, getDeploymentPatternSchema } from "./tools/get-deployment-pattern.js";
import { getDeploymentSteps, getDeploymentStepsSchema } from "./tools/get-deployment-steps.js";

// Execution tool implementations
import { applyManifest, applyManifestSchema } from "./tools/apply-manifest.js";

// Resource implementations
import { getServicesInventory } from "./resources/services.js";
import { getTemplatesCatalog } from "./resources/templates.js";
import { getArchitectureOverview } from "./resources/architecture.js";

// Create server instance
const server = new McpServer({
  name: "proxmox-k8s",
  version: "1.0.0",
});

// ============================================================================
// QUERY TOOLS - For researcher and planner subagents
// ============================================================================

server.tool(
  "list_services",
  "List all deployed services in the Kubernetes cluster. Returns service names, namespaces, and status.",
  listServicesSchema,
  listServices
);

server.tool(
  "get_service_info",
  "Get detailed information about a specific service including pods, endpoints, ingress, and ArgoCD status.",
  getServiceInfoSchema,
  getServiceInfo
);

server.tool(
  "check_health",
  "Check the health status of a deployed service. Runs 7 checks: pods, endpoints, ingress, certificate, ArgoCD, DNS, HTTP.",
  checkHealthSchema,
  checkHealth
);

server.tool(
  "get_capability_options",
  "Get options for adding a capability (database, cache, queue, storage, etc.). Returns existing resources, new options, and questions to consider.",
  getCapabilityOptionsSchema,
  getCapabilityOptions
);

server.tool(
  "get_deployment_pattern",
  "Get the recommended deployment pattern and template for a given application type (e.g., 'python-api', 'frontend', 'database').",
  getDeploymentPatternSchema,
  getDeploymentPattern
);

server.tool(
  "get_deployment_steps",
  "Get the detailed steps needed to deploy an application. Returns prerequisites, ordered steps with commands, and rollback instructions.",
  getDeploymentStepsSchema,
  getDeploymentSteps
);

// ============================================================================
// EXECUTION TOOLS - For executor subagent only, after plan approval
// ============================================================================

server.tool(
  "apply_manifest",
  "Apply a Kubernetes manifest. Minimal execution tool for use after a deployment plan has been approved. Supports dry-run mode.",
  applyManifestSchema,
  applyManifest
);

// ============================================================================
// RESOURCES - Static/dynamic information sources
// ============================================================================

server.resource(
  "services://inventory",
  "Current inventory of all deployed services with live status from cluster",
  async () => {
    const content = await getServicesInventory();
    return {
      contents: [{
        uri: "services://inventory",
        mimeType: "application/json",
        text: content,
      }],
    };
  }
);

server.resource(
  "templates://catalog",
  "Available deployment templates and their descriptions",
  async () => {
    const content = await getTemplatesCatalog();
    return {
      contents: [{
        uri: "templates://catalog",
        mimeType: "application/json",
        text: content,
      }],
    };
  }
);

server.resource(
  "architecture://overview",
  "Architecture overview extracted from CLAUDE.md",
  async () => {
    const content = await getArchitectureOverview();
    return {
      contents: [{
        uri: "architecture://overview",
        mimeType: "text/markdown",
        text: content,
      }],
    };
  }
);

// ============================================================================
// SERVER STARTUP
// ============================================================================

async function runStdioTransport() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Proxmox K8s MCP server running on stdio");
  console.error("Query tools: list_services, get_service_info, check_health, get_capability_options, get_deployment_pattern, get_deployment_steps");
  console.error("Execution tools: apply_manifest");
}

async function runHttpTransport() {
  const app = express();
  app.use(express.json());

  // Create HTTP transport
  const httpTransport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined, // Stateless mode
  });

  // Handle MCP requests
  app.post("/mcp", async (req, res) => {
    try {
      await httpTransport.handleRequest(req, res, req.body);
    } catch (error) {
      console.error("Error handling MCP request:", error);
      if (!res.headersSent) {
        res.status(500).json({ error: "Internal server error" });
      }
    }
  });

  // Health check endpoint
  app.get("/health", (req, res) => {
    res.json({ status: "healthy", transport: "streamable-http" });
  });

  // Connect server to transport
  await server.connect(httpTransport);

  const port = parseInt(process.env.PORT || "8000");
  const host = process.env.HOST || "0.0.0.0";

  app.listen(port, host, () => {
    console.error(`Proxmox K8s MCP server running on http://${host}:${port}`);
    console.error("MCP endpoint: POST /mcp");
    console.error("Health check: GET /health");
    console.error("Query tools: list_services, get_service_info, check_health, get_capability_options, get_deployment_pattern, get_deployment_steps");
    console.error("Execution tools: apply_manifest");
  });
}

async function main() {
  // Select transport based on environment
  const transport = process.env.MCP_TRANSPORT || "stdio";

  if (transport === "streamable-http" || transport === "http") {
    await runHttpTransport();
  } else {
    await runStdioTransport();
  }
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
