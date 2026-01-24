/**
 * list_services tool
 *
 * Lists all deployed services in the cluster by combining:
 * - apps.json registry (catalog)
 * - kubectl live status
 */

import { z } from "zod";
import { readRegistry } from "../clients/registry.js";
import { getPods, getServices, getApplications } from "../clients/kubernetes.js";

export const listServicesSchema = {
  namespace: z.string().optional().describe("Filter by namespace (default: all)"),
  includeSystem: z.boolean().optional().describe("Include system namespaces like kube-system (default: false)"),
};

const SYSTEM_NAMESPACES = ["kube-system", "kube-public", "kube-node-lease"];

export async function listServices(params: {
  namespace?: string;
  includeSystem?: boolean;
}): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const { namespace, includeSystem = false } = params;

  // Get registry data
  const registry = readRegistry();

  // Get live cluster data
  const pods = getPods(namespace);
  const services = getServices(namespace);
  const applications = getApplications();

  // Filter out system namespaces unless requested
  const filteredPods = includeSystem
    ? pods
    : pods.filter((p) => !SYSTEM_NAMESPACES.includes(p.namespace));

  const filteredServices = includeSystem
    ? services
    : services.filter((s) => !SYSTEM_NAMESPACES.includes(s.namespace));

  // Group pods by namespace
  const namespaces = new Set(filteredPods.map((p) => p.namespace));

  // Build summary
  const summary: any = {
    registeredApps: registry.apps.length,
    liveNamespaces: Array.from(namespaces),
    argocdApplications: applications.length,
    services: [],
  };

  // Merge registry with live status
  for (const app of registry.apps) {
    const livePods = filteredPods.filter(
      (p) => p.namespace === app.namespace && p.name.startsWith(app.name)
    );
    const argoApp = applications.find((a) => a.name === app.name);

    summary.services.push({
      name: app.name,
      namespace: app.namespace,
      type: app.type,
      url: app.url,
      status: {
        pods: livePods.length > 0 ? `${livePods.filter(p => p.status === "Running").length}/${livePods.length} running` : "no pods",
        argocd: argoApp ? `${argoApp.syncStatus}/${argoApp.healthStatus}` : "not managed",
      },
    });
  }

  // Add any live services not in registry
  const registeredNames = new Set(registry.apps.map((a) => a.name));
  for (const svc of filteredServices) {
    if (!registeredNames.has(svc.name) && svc.name !== "kubernetes") {
      summary.services.push({
        name: svc.name,
        namespace: svc.namespace,
        type: svc.type === "LoadBalancer" ? "loadbalancer" : "service",
        url: null,
        status: {
          pods: "unknown",
          argocd: "not managed",
        },
        note: "Not in registry",
      });
    }
  }

  return {
    content: [{
      type: "text",
      text: JSON.stringify(summary, null, 2),
    }],
  };
}
