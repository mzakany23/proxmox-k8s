#!/usr/bin/env node
/**
 * Agent Progress MCP Server
 *
 * MCP server for tracking and visualizing concurrent agent progress.
 * Provides tools for workflow management and agent tracking with DAG visualization support.
 *
 * Tools:
 * - create_workflow: Create a new workflow session
 * - create_agent: Register an agent with parent relationship
 * - update_agent: Update agent status/progress
 * - get_workflow_dag: Get full DAG structure for visualization
 * - list_workflows: List all workflows
 *
 * Resources:
 * - workflows://active: Current active workflows
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

// Tool implementations
import { createWorkflowTool, createWorkflowSchema } from "./tools/create-workflow.js";
import { createAgentTool, createAgentSchema } from "./tools/create-agent.js";
import { updateAgentTool, updateAgentSchema } from "./tools/update-agent.js";
import { getWorkflowDAGTool, getWorkflowDAGSchema } from "./tools/get-workflow-dag.js";
import { listWorkflowsTool, listWorkflowsSchema } from "./tools/list-workflows.js";

// Database client
import { listWorkflows, testConnection } from "./clients/database.js";

// Create server instance
const server = new McpServer({
  name: "agent-progress",
  version: "1.0.0",
});

// ============================================================================
// TOOLS
// ============================================================================

server.tool(
  "create_workflow",
  "Create a new workflow session for tracking agents. Returns the workflow ID.",
  createWorkflowSchema,
  createWorkflowTool
);

server.tool(
  "create_agent",
  "Register a new agent with optional parent relationship for DAG visualization.",
  createAgentSchema,
  createAgentTool
);

server.tool(
  "update_agent",
  "Update an agent's status, progress, or metadata.",
  updateAgentSchema,
  updateAgentTool
);

server.tool(
  "get_workflow_dag",
  "Get the full DAG structure for a workflow including all agents and edges.",
  getWorkflowDAGSchema,
  getWorkflowDAGTool
);

server.tool(
  "list_workflows",
  "List all workflows with agent counts and status breakdown.",
  listWorkflowsSchema,
  listWorkflowsTool
);

// ============================================================================
// RESOURCES
// ============================================================================

server.resource(
  "workflows://active",
  "Current active workflows with agent counts",
  async () => {
    const workflows = await listWorkflows();
    return {
      contents: [
        {
          uri: "workflows://active",
          mimeType: "application/json",
          text: JSON.stringify(workflows, null, 2),
        },
      ],
    };
  }
);

// ============================================================================
// SERVER STARTUP
// ============================================================================

async function runStdioTransport() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Agent Progress MCP server running on stdio");
  console.error("Tools: create_workflow, create_agent, update_agent, get_workflow_dag, list_workflows");
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
    console.error(`Agent Progress MCP server running on http://${host}:${port}`);
    console.error("MCP endpoint: POST /mcp");
    console.error("Health check: GET /health");
    console.error("Tools: create_workflow, create_agent, update_agent, get_workflow_dag, list_workflows");
  });
}

async function main() {
  // Test database connection
  const dbConnected = await testConnection();
  if (!dbConnected) {
    console.error("Warning: Could not connect to database. Some features may not work.");
  }

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
