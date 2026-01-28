/**
 * get_workflow_dag tool
 *
 * Returns the full DAG structure for a workflow
 */

import { z } from "zod";
import { getWorkflowDAG } from "../clients/database.js";

export const getWorkflowDAGSchema = {
  workflowId: z.string().uuid().describe("ID of the workflow to get DAG for"),
};

export async function getWorkflowDAGTool(params: {
  workflowId: string;
}): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const dag = await getWorkflowDAG(params.workflowId);

  if (!dag) {
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              success: false,
              error: `Workflow with ID ${params.workflowId} not found`,
            },
            null,
            2
          ),
        },
      ],
    };
  }

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(
          {
            success: true,
            dag: {
              workflowId: dag.workflowId,
              workflowName: dag.workflowName,
              workflowStatus: dag.workflowStatus,
              nodeCount: dag.nodes.length,
              edgeCount: dag.edges.length,
              nodes: dag.nodes,
              edges: dag.edges,
            },
          },
          null,
          2
        ),
      },
    ],
  };
}
