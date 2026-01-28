/**
 * Database client for agent progress storage
 */

import pg from "pg";

const { Pool } = pg;

// Database configuration from environment
const pool = new Pool({
  host: process.env.POSTGRES_HOST || "localhost",
  port: parseInt(process.env.POSTGRES_PORT || "5436"),
  database: process.env.POSTGRES_DB || "agent_progress",
  user: process.env.POSTGRES_USER || "postgres",
  password: process.env.POSTGRES_PASSWORD || "postgres",
});

export interface Workflow {
  id: string;
  name: string;
  status: string;
  metadata: Record<string, unknown>;
  created_at: Date;
}

export interface Agent {
  id: string;
  workflow_id: string;
  parent_id: string | null;
  name: string;
  agent_type: string;
  status: string;
  progress: number;
  metadata: Record<string, unknown>;
  started_at: Date | null;
  completed_at: Date | null;
  created_at: Date;
}

export interface AgentEvent {
  id: number;
  agent_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: Date;
}

// Workflow operations
export async function createWorkflow(
  name: string,
  metadata: Record<string, unknown> = {}
): Promise<Workflow> {
  const result = await pool.query(
    `INSERT INTO workflows (id, name, status, metadata)
     VALUES (gen_random_uuid(), $1, 'pending', $2)
     RETURNING *`,
    [name, JSON.stringify(metadata)]
  );
  return result.rows[0];
}

export async function getWorkflow(id: string): Promise<Workflow | null> {
  const result = await pool.query("SELECT * FROM workflows WHERE id = $1", [id]);
  return result.rows[0] || null;
}

export async function listWorkflows(
  status?: string
): Promise<Workflow[]> {
  let query = "SELECT * FROM workflows";
  const params: string[] = [];

  if (status) {
    query += " WHERE status = $1";
    params.push(status);
  }

  query += " ORDER BY created_at DESC";
  const result = await pool.query(query, params);
  return result.rows;
}

export async function updateWorkflowStatus(
  id: string,
  status: string
): Promise<Workflow | null> {
  const result = await pool.query(
    "UPDATE workflows SET status = $1 WHERE id = $2 RETURNING *",
    [status, id]
  );
  return result.rows[0] || null;
}

// Agent operations
export async function createAgent(params: {
  workflowId: string;
  parentId?: string;
  name: string;
  agentType: string;
  metadata?: Record<string, unknown>;
}): Promise<Agent> {
  const result = await pool.query(
    `INSERT INTO agents (id, workflow_id, parent_id, name, agent_type, status, progress, metadata)
     VALUES (gen_random_uuid(), $1, $2, $3, $4, 'pending', 0, $5)
     RETURNING *`,
    [
      params.workflowId,
      params.parentId || null,
      params.name,
      params.agentType,
      JSON.stringify(params.metadata || {}),
    ]
  );
  return result.rows[0];
}

export async function getAgent(id: string): Promise<Agent | null> {
  const result = await pool.query("SELECT * FROM agents WHERE id = $1", [id]);
  return result.rows[0] || null;
}

export async function updateAgent(
  id: string,
  updates: {
    status?: string;
    progress?: number;
    metadata?: Record<string, unknown>;
  }
): Promise<Agent | null> {
  const setClauses: string[] = [];
  const values: unknown[] = [];
  let paramIndex = 1;

  if (updates.status !== undefined) {
    setClauses.push(`status = $${paramIndex++}`);
    values.push(updates.status);

    // Auto-set timestamps based on status
    if (updates.status === "running") {
      setClauses.push(`started_at = COALESCE(started_at, NOW())`);
    } else if (updates.status === "completed" || updates.status === "failed") {
      setClauses.push(`completed_at = NOW()`);
    }
  }

  if (updates.progress !== undefined) {
    setClauses.push(`progress = $${paramIndex++}`);
    values.push(updates.progress);
  }

  if (updates.metadata !== undefined) {
    setClauses.push(`metadata = metadata || $${paramIndex++}::jsonb`);
    values.push(JSON.stringify(updates.metadata));
  }

  if (setClauses.length === 0) {
    return getAgent(id);
  }

  values.push(id);
  const result = await pool.query(
    `UPDATE agents SET ${setClauses.join(", ")} WHERE id = $${paramIndex} RETURNING *`,
    values
  );
  return result.rows[0] || null;
}

export async function getWorkflowAgents(workflowId: string): Promise<Agent[]> {
  const result = await pool.query(
    "SELECT * FROM agents WHERE workflow_id = $1 ORDER BY created_at",
    [workflowId]
  );
  return result.rows;
}

// DAG structure for visualization
export interface DAGNode {
  id: string;
  name: string;
  agentType: string;
  status: string;
  progress: number;
  parentId: string | null;
  metadata: Record<string, unknown>;
  startedAt: Date | null;
  completedAt: Date | null;
}

export interface DAGStructure {
  workflowId: string;
  workflowName: string;
  workflowStatus: string;
  nodes: DAGNode[];
  edges: Array<{ source: string; target: string }>;
}

export async function getWorkflowDAG(workflowId: string): Promise<DAGStructure | null> {
  const workflow = await getWorkflow(workflowId);
  if (!workflow) return null;

  const agents = await getWorkflowAgents(workflowId);

  const nodes: DAGNode[] = agents.map((a) => ({
    id: a.id,
    name: a.name,
    agentType: a.agent_type,
    status: a.status,
    progress: a.progress,
    parentId: a.parent_id,
    metadata: a.metadata,
    startedAt: a.started_at,
    completedAt: a.completed_at,
  }));

  const edges = agents
    .filter((a) => a.parent_id)
    .map((a) => ({
      source: a.parent_id!,
      target: a.id,
    }));

  return {
    workflowId: workflow.id,
    workflowName: workflow.name,
    workflowStatus: workflow.status,
    nodes,
    edges,
  };
}

// Event logging
export async function createAgentEvent(
  agentId: string,
  eventType: string,
  payload: Record<string, unknown> = {}
): Promise<AgentEvent> {
  const result = await pool.query(
    `INSERT INTO agent_events (agent_id, event_type, payload)
     VALUES ($1, $2, $3)
     RETURNING *`,
    [agentId, eventType, JSON.stringify(payload)]
  );
  return result.rows[0];
}

export async function getAgentEvents(agentId: string): Promise<AgentEvent[]> {
  const result = await pool.query(
    "SELECT * FROM agent_events WHERE agent_id = $1 ORDER BY created_at",
    [agentId]
  );
  return result.rows;
}

// Test connection
export async function testConnection(): Promise<boolean> {
  try {
    await pool.query("SELECT 1");
    return true;
  } catch {
    return false;
  }
}

export { pool };
