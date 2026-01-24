/**
 * get_service_info tool
 *
 * Get detailed information about a specific service
 */

import { z } from "zod";
import { getApp } from "../clients/registry.js";
import {
  kubectl,
  getPods,
  getServices,
  getIngresses,
  describe,
  resourceExists,
} from "../clients/kubernetes.js";

export const getServiceInfoSchema = {
  name: z.string().describe("Name of the service to get info for"),
  namespace: z.string().optional().describe("Namespace (default: apps)"),
};

export async function getServiceInfo(params: {
  name: string;
  namespace?: string;
}): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const { name, namespace = "apps" } = params;

  const info: any = {
    name,
    namespace,
    registry: null,
    pods: [],
    services: [],
    ingress: null,
    argocd: null,
    certificate: null,
    endpoints: null,
  };

  // Check registry
  const registryEntry = getApp(name);
  if (registryEntry) {
    info.registry = registryEntry;
  }

  // Get pods
  const allPods = getPods(namespace);
  info.pods = allPods.filter(
    (p) => p.name.startsWith(name) || p.name.includes(name)
  );

  // Get services
  const allServices = getServices(namespace);
  info.services = allServices.filter(
    (s) => s.name === name || s.name.startsWith(name)
  );

  // Get ingress
  const allIngresses = getIngresses(namespace);
  const ingress = allIngresses.find((i) => i.name === name);
  if (ingress) {
    info.ingress = ingress;
  }

  // Check ArgoCD application
  try {
    if (resourceExists("application", name, "argocd")) {
      const appJson = kubectl(`get application ${name} -n argocd -o json`);
      const app = JSON.parse(appJson);
      info.argocd = {
        syncStatus: app.status?.sync?.status || "Unknown",
        healthStatus: app.status?.health?.status || "Unknown",
        repo: app.spec?.source?.repoURL || null,
        path: app.spec?.source?.path || null,
        targetRevision: app.spec?.source?.targetRevision || null,
      };
    }
  } catch {
    // ArgoCD app doesn't exist
  }

  // Check certificate
  try {
    const certName = `${name}-tls`;
    if (resourceExists("certificate", certName, namespace)) {
      const certJson = kubectl(`get certificate ${certName} -n ${namespace} -o json`);
      const cert = JSON.parse(certJson);
      info.certificate = {
        name: certName,
        ready: cert.status?.conditions?.find((c: any) => c.type === "Ready")?.status === "True",
        issuer: cert.spec?.issuerRef?.name || null,
        dnsNames: cert.spec?.dnsNames || [],
      };
    }
  } catch {
    // Certificate doesn't exist
  }

  // Get endpoints
  try {
    const epJson = kubectl(`get endpoints ${name} -n ${namespace} -o json 2>/dev/null || echo "{}"`);
    const ep = JSON.parse(epJson);
    if (ep.subsets) {
      info.endpoints = ep.subsets.flatMap((s: any) =>
        (s.addresses || []).map((a: any) => a.ip)
      );
    }
  } catch {
    // No endpoints
  }

  // Summary
  info.summary = {
    healthy: info.pods.every((p: any) => p.status === "Running") && info.pods.length > 0,
    accessible: info.ingress?.address ? true : false,
    argocdManaged: info.argocd !== null,
    tlsReady: info.certificate?.ready || false,
  };

  return {
    content: [{
      type: "text",
      text: JSON.stringify(info, null, 2),
    }],
  };
}
