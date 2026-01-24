/**
 * services://inventory resource
 *
 * Returns current inventory of all deployed services with live status
 */

import { readRegistry } from "../clients/registry.js";
import { getPods, getServices, getApplications, getIngresses } from "../clients/kubernetes.js";

interface ServiceInventoryItem {
  name: string;
  namespace: string;
  type: string;
  url?: string;
  status: {
    pods: string;
    argocd: string;
    ingress: string;
  };
  repo?: string;
}

export async function getServicesInventory(): Promise<string> {
  const registry = readRegistry();
  const pods = getPods();
  const services = getServices();
  const applications = getApplications();
  const ingresses = getIngresses();

  const inventory: ServiceInventoryItem[] = [];

  // Process registered apps
  for (const app of registry.apps) {
    const appPods = pods.filter(
      (p) => p.namespace === app.namespace && (p.name.startsWith(app.name) || p.name.includes(app.name))
    );
    const argoApp = applications.find((a) => a.name === app.name);
    const ingress = ingresses.find((i) => i.name === app.name || i.hosts.some((h) => h.includes(app.name)));

    const runningPods = appPods.filter((p) => p.status === "Running").length;
    const totalPods = appPods.length;

    inventory.push({
      name: app.name,
      namespace: app.namespace,
      type: app.type,
      url: app.url,
      status: {
        pods: totalPods > 0 ? `${runningPods}/${totalPods}` : "none",
        argocd: argoApp ? `${argoApp.syncStatus}/${argoApp.healthStatus}` : "unmanaged",
        ingress: ingress?.address || "none",
      },
      repo: app.repo,
    });
  }

  // Add ArgoCD apps not in registry
  const registeredNames = new Set(registry.apps.map((a) => a.name));
  for (const app of applications) {
    if (!registeredNames.has(app.name)) {
      const appPods = pods.filter((p) => p.name.includes(app.name));
      const runningPods = appPods.filter((p) => p.status === "Running").length;

      inventory.push({
        name: app.name,
        namespace: "argocd-managed",
        type: "argocd-app",
        status: {
          pods: appPods.length > 0 ? `${runningPods}/${appPods.length}` : "unknown",
          argocd: `${app.syncStatus}/${app.healthStatus}`,
          ingress: "unknown",
        },
      });
    }
  }

  const result = {
    timestamp: new Date().toISOString(),
    summary: {
      totalApps: inventory.length,
      healthy: inventory.filter((i) => i.status.argocd.includes("Healthy")).length,
      synced: inventory.filter((i) => i.status.argocd.includes("Synced")).length,
    },
    services: inventory,
  };

  return JSON.stringify(result, null, 2);
}
