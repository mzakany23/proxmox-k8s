/**
 * get_capability_options tool
 *
 * Returns information about options for adding a capability.
 * Read-only - provides facts and questions, doesn't execute anything.
 * Designed to feed into the researcher → planner → executor workflow.
 */

import { z } from "zod";
import { getPods, getServices, resourceExists } from "../clients/kubernetes.js";
import { readRegistry } from "../clients/registry.js";

export const getCapabilityOptionsSchema = {
  capability: z.enum([
    "database",
    "cache",
    "queue",
    "storage",
    "monitoring",
    "logging",
    "auth",
    "search",
  ]).describe("Type of capability needed"),
  requirements: z.string().optional().describe("Specific requirements or context"),
};

interface CapabilityOption {
  name: string;
  method: string;
  description: string;
  effort: "low" | "medium" | "high";
  resources?: string;
  helmChart?: string;
  helmRepo?: string;
}

interface ExistingResource {
  name: string;
  namespace: string;
  type: string;
  canReuse: boolean;
  connectionInfo?: string;
}

interface CapabilityResponse {
  capability: string;
  requirements: string | null;
  existingResources: ExistingResource[];
  newOptions: CapabilityOption[];
  questions: string[];
  considerations: string[];
  relatedSkills: string[];
}

const CAPABILITY_DEFINITIONS: Record<string, {
  searchTerms: string[];
  options: CapabilityOption[];
  questions: string[];
  considerations: string[];
}> = {
  database: {
    searchTerms: ["postgres", "postgresql", "mysql", "mariadb", "mongodb"],
    options: [
      {
        name: "Use shared Postgres",
        method: "shared",
        description: "Create database in existing Postgres instance (gitea namespace)",
        effort: "low",
        resources: "None - uses existing",
      },
      {
        name: "PostgreSQL (Helm)",
        method: "helm",
        description: "Deploy dedicated PostgreSQL instance",
        effort: "medium",
        helmChart: "postgresql",
        helmRepo: "bitnami",
        resources: "256Mi-1Gi memory, 1-10Gi storage",
      },
      {
        name: "MySQL (Helm)",
        method: "helm",
        description: "Deploy MySQL/MariaDB instance",
        effort: "medium",
        helmChart: "mysql",
        helmRepo: "bitnami",
        resources: "256Mi-1Gi memory, 1-10Gi storage",
      },
    ],
    questions: [
      "Can you use the shared Postgres or do you need isolation?",
      "What's the expected data size?",
      "Do you need high availability (multiple replicas)?",
      "Any specific version requirements?",
    ],
    considerations: [
      "Shared Postgres reduces resource usage and maintenance",
      "Dedicated instance needed for: different version, isolation, heavy load",
      "Remember to create secrets for credentials",
    ],
  },
  cache: {
    searchTerms: ["redis", "memcached", "valkey"],
    options: [
      {
        name: "Redis (Helm)",
        method: "helm",
        description: "Deploy Redis for caching/sessions",
        effort: "low",
        helmChart: "redis",
        helmRepo: "bitnami",
        resources: "128Mi-512Mi memory",
      },
      {
        name: "Redis Cluster (Helm)",
        method: "helm",
        description: "Deploy Redis with clustering for HA",
        effort: "medium",
        helmChart: "redis-cluster",
        helmRepo: "bitnami",
        resources: "512Mi-2Gi memory",
      },
      {
        name: "Valkey (Helm)",
        method: "helm",
        description: "Open-source Redis alternative",
        effort: "medium",
        helmChart: "valkey",
        helmRepo: "bitnami",
        resources: "128Mi-512Mi memory",
      },
    ],
    questions: [
      "Is this for session storage, caching, or pub/sub?",
      "Do you need persistence or is in-memory acceptable?",
      "Single instance or clustered for HA?",
    ],
    considerations: [
      "For simple caching, single Redis instance is sufficient",
      "Enable persistence if data must survive restarts",
      "Consider memory limits carefully - Redis is memory-bound",
    ],
  },
  queue: {
    searchTerms: ["rabbitmq", "kafka", "nats", "activemq"],
    options: [
      {
        name: "RabbitMQ (Helm)",
        method: "helm",
        description: "Deploy RabbitMQ message broker",
        effort: "medium",
        helmChart: "rabbitmq",
        helmRepo: "bitnami",
        resources: "256Mi-1Gi memory",
      },
      {
        name: "NATS (Helm)",
        method: "helm",
        description: "Lightweight message queue",
        effort: "low",
        helmChart: "nats",
        helmRepo: "nats",
        resources: "64Mi-256Mi memory",
      },
      {
        name: "Kafka (Helm)",
        method: "helm",
        description: "Distributed event streaming (heavy)",
        effort: "high",
        helmChart: "kafka",
        helmRepo: "bitnami",
        resources: "1Gi+ memory, requires Zookeeper",
      },
    ],
    questions: [
      "What messaging pattern? (pub/sub, work queues, request/reply)",
      "Expected message volume?",
      "Do you need message persistence?",
      "Any specific protocol requirements (AMQP, MQTT, etc.)?",
    ],
    considerations: [
      "NATS is lightweight, good for simple use cases",
      "RabbitMQ is versatile, good default choice",
      "Kafka is heavy - only use for high-volume streaming",
    ],
  },
  storage: {
    searchTerms: ["minio", "s3", "nfs", "longhorn"],
    options: [
      {
        name: "MinIO (Helm)",
        method: "helm",
        description: "S3-compatible object storage",
        effort: "medium",
        helmChart: "minio",
        helmRepo: "bitnami",
        resources: "512Mi memory, 10Gi+ storage",
      },
      {
        name: "NFS Provisioner",
        method: "helm",
        description: "Network file storage for ReadWriteMany",
        effort: "medium",
        helmChart: "nfs-subdir-external-provisioner",
        helmRepo: "nfs-subdir-external-provisioner",
        resources: "Requires NFS server",
      },
    ],
    questions: [
      "Object storage (S3-like) or file storage (NFS)?",
      "Expected storage size?",
      "Do multiple pods need to write to same volume?",
    ],
    considerations: [
      "MinIO provides S3 API compatibility",
      "NFS needed for ReadWriteMany access mode",
      "Consider backup strategy for persistent data",
    ],
  },
  monitoring: {
    searchTerms: ["prometheus", "grafana", "alertmanager", "loki"],
    options: [
      {
        name: "Prometheus Stack (exists)",
        method: "existing",
        description: "Already deployed in monitoring namespace",
        effort: "low",
      },
      {
        name: "Add Grafana Dashboard",
        method: "config",
        description: "Add dashboard to existing Grafana",
        effort: "low",
      },
      {
        name: "Loki (Helm)",
        method: "helm",
        description: "Log aggregation for Grafana",
        effort: "medium",
        helmChart: "loki-stack",
        helmRepo: "grafana",
        resources: "512Mi-2Gi memory",
      },
    ],
    questions: [
      "Metrics, logs, or traces?",
      "Need alerting configured?",
      "Custom dashboards needed?",
    ],
    considerations: [
      "Prometheus + Grafana already deployed",
      "Add ServiceMonitor for auto-discovery",
      "Loki adds log aggregation capability",
    ],
  },
  logging: {
    searchTerms: ["loki", "elasticsearch", "fluentd", "fluentbit"],
    options: [
      {
        name: "Loki + Promtail (Helm)",
        method: "helm",
        description: "Lightweight log aggregation for Grafana",
        effort: "medium",
        helmChart: "loki-stack",
        helmRepo: "grafana",
        resources: "512Mi-1Gi memory",
      },
      {
        name: "Fluent Bit (Helm)",
        method: "helm",
        description: "Log forwarder to external system",
        effort: "medium",
        helmChart: "fluent-bit",
        helmRepo: "fluent",
        resources: "64Mi-256Mi memory",
      },
    ],
    questions: [
      "Where should logs be stored/forwarded?",
      "Retention period needed?",
      "Need to query logs in Grafana?",
    ],
    considerations: [
      "Loki integrates well with existing Grafana",
      "Fluent Bit good for forwarding to external systems",
    ],
  },
  auth: {
    searchTerms: ["keycloak", "authentik", "authelia", "oauth", "oidc"],
    options: [
      {
        name: "Authelia (exists)",
        method: "existing",
        description: "Already deployed for 2FA/SSO",
        effort: "low",
      },
      {
        name: "Keycloak (Helm)",
        method: "helm",
        description: "Full-featured identity provider",
        effort: "high",
        helmChart: "keycloak",
        helmRepo: "bitnami",
        resources: "512Mi-2Gi memory, requires Postgres",
      },
    ],
    questions: [
      "Need SSO/OIDC provider or just authentication proxy?",
      "How many users/applications?",
      "External identity providers to integrate?",
    ],
    considerations: [
      "Authelia already handles ingress authentication",
      "Keycloak for full OIDC/SAML provider needs",
    ],
  },
  search: {
    searchTerms: ["elasticsearch", "opensearch", "meilisearch", "typesense"],
    options: [
      {
        name: "Meilisearch (Helm)",
        method: "helm",
        description: "Lightweight, fast search engine",
        effort: "low",
        helmChart: "meilisearch",
        helmRepo: "meilisearch",
        resources: "256Mi-1Gi memory",
      },
      {
        name: "OpenSearch (Helm)",
        method: "helm",
        description: "Elasticsearch fork, full-featured",
        effort: "high",
        helmChart: "opensearch",
        helmRepo: "opensearch",
        resources: "2Gi+ memory",
      },
    ],
    questions: [
      "Simple search or complex analytics?",
      "Expected index size?",
      "Need full-text search features?",
    ],
    considerations: [
      "Meilisearch is simple and fast for most use cases",
      "OpenSearch/Elasticsearch for complex analytics, heavy",
    ],
  },
};

export async function getCapabilityOptions(params: {
  capability: string;
  requirements?: string;
}): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const { capability, requirements } = params;

  const definition = CAPABILITY_DEFINITIONS[capability];
  if (!definition) {
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          error: `Unknown capability: ${capability}`,
          available: Object.keys(CAPABILITY_DEFINITIONS),
        }, null, 2),
      }],
    };
  }

  // Search for existing resources
  const existingResources: ExistingResource[] = [];
  const pods = getPods();
  const registry = readRegistry();

  for (const term of definition.searchTerms) {
    // Check pods
    const matchingPods = pods.filter((p) =>
      p.name.toLowerCase().includes(term) ||
      p.namespace.toLowerCase().includes(term)
    );

    for (const pod of matchingPods) {
      if (!existingResources.find((r) => r.name === pod.name)) {
        existingResources.push({
          name: pod.name,
          namespace: pod.namespace,
          type: term,
          canReuse: pod.status === "Running",
          connectionInfo: `${pod.name}.${pod.namespace}.svc.cluster.local`,
        });
      }
    }

    // Check registry
    const matchingApps = registry.apps.filter((a) =>
      a.name.toLowerCase().includes(term) ||
      a.type?.toLowerCase().includes(term)
    );

    for (const app of matchingApps) {
      if (!existingResources.find((r) => r.name === app.name)) {
        existingResources.push({
          name: app.name,
          namespace: app.namespace,
          type: app.type,
          canReuse: true,
          connectionInfo: app.url,
        });
      }
    }
  }

  // Build response
  const response: CapabilityResponse = {
    capability,
    requirements: requirements || null,
    existingResources,
    newOptions: definition.options,
    questions: definition.questions,
    considerations: definition.considerations,
    relatedSkills: capability === "database" ? ["gitea-auth"] : [],
  };

  // Add context-specific notes
  if (existingResources.length > 0) {
    response.considerations.unshift(
      `Found ${existingResources.length} existing ${capability} resource(s) that may be reusable`
    );
  }

  return {
    content: [{
      type: "text",
      text: JSON.stringify(response, null, 2),
    }],
  };
}
