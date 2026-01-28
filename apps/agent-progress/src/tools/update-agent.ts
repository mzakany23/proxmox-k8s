/**
 * update_agent tool
 *
 * Updates an agent's status, progress, or metadata
 */

import { z } from "zod";
import { updateAgent, createAgentEvent, getAgent } from "../clients/database.js";

export const updateAgentSchema = {
  agentId: z.string().uuid().describe("ID of the agent to update"),
  status: z
    .enum(["pending", "running", "completed", "failed"])
    .optional()
    .describe("New status for the agent"),
  progress: z
    .number()
    .min(0)
    .max(100)
    .optional()
    .describe("Progress percentage (0-100)"),
  metadata: z.record(z.unknown()).optional().describe("Metadata to merge into the agent"),
};

export async function updateAgentTool(params: {
  agentId: string;
  status?: "pending" | "running" | "completed" | "failed";
  progress?: number;
  metadata?: Record<string, unknown>;
}): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const existingAgent = await getAgent(params.agentId);
  if (!existingAgent) {
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              success: false,
              error: `Agent with ID ${params.agentId} not found`,
            },
            null,
            2
          ),
        },
      ],
    };
  }

  const agent = await updateAgent(params.agentId, {
    status: params.status,
    progress: params.progress,
    metadata: params.metadata,
  });

  if (!agent) {
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              success: false,
              error: `Failed to update agent ${params.agentId}`,
            },
            null,
            2
          ),
        },
      ],
    };
  }

  // Log status change event
  if (params.status) {
    await createAgentEvent(agent.id, `status_${params.status}`, {
      previousStatus: existingAgent.status,
      newStatus: params.status,
    });
  }

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(
          {
            success: true,
            agent: {
              id: agent.id,
              name: agent.name,
              status: agent.status,
              progress: agent.progress,
              startedAt: agent.started_at,
              completedAt: agent.completed_at,
            },
            message: `Agent "${agent.name}" updated`,
          },
          null,
          2
        ),
      },
    ],
  };
}
