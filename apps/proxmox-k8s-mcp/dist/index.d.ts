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
 */
export {};
//# sourceMappingURL=index.d.ts.map