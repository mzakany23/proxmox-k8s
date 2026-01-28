/**
 * create_agent tool
 *
 * Registers a new agent with optional parent relationship
 */

import { z } from "zod";
import { createAgent, createAgentEvent, type Agent } from "../clients/database.js";

export const createAgentSchema = {
  workflowId: z.string().uuid().describe("ID of the workflow this agent belongs to"),
  name: z.string().describe("Name/description of the agent"),
  agentType: z.string().describe("Type of agent (e.g., 'Explore', 'Plan', 'Bash', 'general-purpose')"),
  parentId: z.string().uuid().optional().describe("ID of the parent agent (for hierarchical relationships)"),
  metadata: z.record(z.unknown()).optional().describe("Optional metadata for the agent"),
};

export async function createAgentTool(params: {
  workflowId: string;
  name: string;
  agentType: string;
  parentId?: string;
  metadata?: Record<string, unknown>;
}): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const agent = await createAgent({
    workflowId: params.workflowId,
    parentId: params.parentId,
    name: params.name,
    agentType: params.agentType,
    metadata: params.metadata,
  });

  // Log creation event
  await createAgentEvent(agent.id, "created", {
    name: params.name,
    agentType: params.agentType,
    parentId: params.parentId,
  });

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(
          {
            success: true,
            agent: {
              id: agent.id,
              workflowId: agent.workflow_id,
              parentId: agent.parent_id,
              name: agent.name,
              agentType: agent.agent_type,
              status: agent.status,
              createdAt: agent.created_at,
            },
            message: `Agent "${agent.name}" registered with ID ${agent.id}`,
          },
          null,
          2
        ),
      },
    ],
  };
}
