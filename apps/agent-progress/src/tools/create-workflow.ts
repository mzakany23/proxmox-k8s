/**
 * create_workflow tool
 *
 * Creates a new workflow session for tracking agents
 */

import { z } from "zod";
import { createWorkflow, type Workflow } from "../clients/database.js";

export const createWorkflowSchema = {
  name: z.string().describe("Name of the workflow"),
  metadata: z.record(z.unknown()).optional().describe("Optional metadata for the workflow"),
};

export async function createWorkflowTool(params: {
  name: string;
  metadata?: Record<string, unknown>;
}): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const workflow = await createWorkflow(params.name, params.metadata);

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(
          {
            success: true,
            workflow: {
              id: workflow.id,
              name: workflow.name,
              status: workflow.status,
              createdAt: workflow.created_at,
            },
            message: `Workflow "${workflow.name}" created with ID ${workflow.id}`,
          },
          null,
          2
        ),
      },
    ],
  };
}
