/**
 * list_workflows tool
 *
 * Lists all workflows with optional status filter
 */

import { z } from "zod";
import { listWorkflows, getWorkflowAgents } from "../clients/database.js";

export const listWorkflowsSchema = {
  status: z
    .enum(["pending", "running", "completed", "failed"])
    .optional()
    .describe("Filter by workflow status"),
};

export async function listWorkflowsTool(params: {
  status?: "pending" | "running" | "completed" | "failed";
}): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const workflows = await listWorkflows(params.status);

  // Get agent counts for each workflow
  const workflowsWithCounts = await Promise.all(
    workflows.map(async (w) => {
      const agents = await getWorkflowAgents(w.id);
      const statusCounts = agents.reduce(
        (acc, a) => {
          acc[a.status] = (acc[a.status] || 0) + 1;
          return acc;
        },
        {} as Record<string, number>
      );

      return {
        id: w.id,
        name: w.name,
        status: w.status,
        agentCount: agents.length,
        agentsByStatus: statusCounts,
        createdAt: w.created_at,
      };
    })
  );

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(
          {
            success: true,
            count: workflowsWithCounts.length,
            workflows: workflowsWithCounts,
          },
          null,
          2
        ),
      },
    ],
  };
}
