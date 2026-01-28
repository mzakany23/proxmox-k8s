/**
 * check_health tool
 *
 * Comprehensive health check for a deployed service
 */
import { z } from "zod";
import { execSync } from "child_process";
import { kubectl, getPods, getIngresses, resourceExists, } from "../clients/kubernetes.js";
export const checkHealthSchema = {
    name: z.string().describe("Name of the service to check"),
    namespace: z.string().optional().describe("Namespace (default: apps)"),
    url: z.string().optional().describe("Custom URL to check (default: https://<name>.mcztest.com)"),
};
export async function checkHealth(params) {
    const { name, namespace = "apps", url } = params;
    const targetUrl = url || `https://${name}.mcztest.com`;
    const checks = [];
    // 1. Pod status
    try {
        const pods = getPods(namespace).filter((p) => p.name.startsWith(name) || p.name.includes(name));
        if (pods.length === 0) {
            checks.push({
                check: "Pods",
                status: "fail",
                details: "No pods found",
            });
        }
        else {
            const running = pods.filter((p) => p.status === "Running");
            const hasRestarts = pods.some((p) => p.restarts > 0);
            if (running.length === pods.length && !hasRestarts) {
                checks.push({
                    check: "Pods",
                    status: "pass",
                    details: `${running.length}/${pods.length} running, 0 restarts`,
                });
            }
            else if (running.length === pods.length) {
                checks.push({
                    check: "Pods",
                    status: "warn",
                    details: `${running.length}/${pods.length} running, some restarts`,
                });
            }
            else {
                checks.push({
                    check: "Pods",
                    status: "fail",
                    details: `${running.length}/${pods.length} running`,
                });
            }
        }
    }
    catch (error) {
        checks.push({
            check: "Pods",
            status: "fail",
            details: error.message,
        });
    }
    // 2. Service endpoints
    try {
        const epOutput = kubectl(`get endpoints ${name} -n ${namespace} --no-headers 2>/dev/null || echo ""`);
        if (epOutput && !epOutput.includes("<none>")) {
            checks.push({
                check: "Endpoints",
                status: "pass",
                details: "Endpoints available",
            });
        }
        else {
            checks.push({
                check: "Endpoints",
                status: "fail",
                details: "No endpoints available",
            });
        }
    }
    catch {
        checks.push({
            check: "Endpoints",
            status: "skip",
            details: "Could not check endpoints",
        });
    }
    // 3. Ingress
    try {
        const ingresses = getIngresses(namespace);
        const ingress = ingresses.find((i) => i.name === name);
        if (ingress) {
            if (ingress.address) {
                checks.push({
                    check: "Ingress",
                    status: "pass",
                    details: `Address: ${ingress.address}, Hosts: ${ingress.hosts.join(", ")}`,
                });
            }
            else {
                checks.push({
                    check: "Ingress",
                    status: "warn",
                    details: "Ingress exists but no address assigned",
                });
            }
        }
        else {
            checks.push({
                check: "Ingress",
                status: "skip",
                details: "No ingress configured",
            });
        }
    }
    catch {
        checks.push({
            check: "Ingress",
            status: "skip",
            details: "Could not check ingress",
        });
    }
    // 4. Certificate
    try {
        const certName = `${name}-tls`;
        if (resourceExists("certificate", certName, namespace)) {
            const certJson = kubectl(`get certificate ${certName} -n ${namespace} -o json`);
            const cert = JSON.parse(certJson);
            const ready = cert.status?.conditions?.find((c) => c.type === "Ready")?.status === "True";
            checks.push({
                check: "Certificate",
                status: ready ? "pass" : "fail",
                details: ready ? "Certificate ready" : "Certificate not ready",
            });
        }
        else {
            checks.push({
                check: "Certificate",
                status: "skip",
                details: "No certificate configured",
            });
        }
    }
    catch {
        checks.push({
            check: "Certificate",
            status: "skip",
            details: "Could not check certificate",
        });
    }
    // 5. ArgoCD sync status
    try {
        if (resourceExists("application", name, "argocd")) {
            const appJson = kubectl(`get application ${name} -n argocd -o json`);
            const app = JSON.parse(appJson);
            const syncStatus = app.status?.sync?.status || "Unknown";
            const healthStatus = app.status?.health?.status || "Unknown";
            if (syncStatus === "Synced" && healthStatus === "Healthy") {
                checks.push({
                    check: "ArgoCD",
                    status: "pass",
                    details: `${syncStatus}, ${healthStatus}`,
                });
            }
            else if (syncStatus === "Synced") {
                checks.push({
                    check: "ArgoCD",
                    status: "warn",
                    details: `${syncStatus}, ${healthStatus}`,
                });
            }
            else {
                checks.push({
                    check: "ArgoCD",
                    status: "fail",
                    details: `${syncStatus}, ${healthStatus}`,
                });
            }
        }
        else {
            checks.push({
                check: "ArgoCD",
                status: "skip",
                details: "Not managed by ArgoCD",
            });
        }
    }
    catch {
        checks.push({
            check: "ArgoCD",
            status: "skip",
            details: "Could not check ArgoCD status",
        });
    }
    // 6. DNS resolution
    try {
        const hostname = new URL(targetUrl).hostname;
        const result = execSync(`dig +short ${hostname}`, { encoding: "utf-8" }).trim();
        if (result) {
            checks.push({
                check: "DNS",
                status: "pass",
                details: `Resolves to ${result}`,
            });
        }
        else {
            checks.push({
                check: "DNS",
                status: "fail",
                details: "No DNS record found",
            });
        }
    }
    catch {
        checks.push({
            check: "DNS",
            status: "fail",
            details: "DNS lookup failed",
        });
    }
    // 7. HTTP check
    try {
        const httpCode = execSync(`curl -sk -o /dev/null -w "%{http_code}" "${targetUrl}" --connect-timeout 5`, { encoding: "utf-8" }).trim();
        const code = parseInt(httpCode);
        if (code >= 200 && code < 400) {
            checks.push({
                check: "HTTP",
                status: "pass",
                details: `HTTP ${code}`,
            });
        }
        else if (code === 0) {
            checks.push({
                check: "HTTP",
                status: "fail",
                details: "Connection failed",
            });
        }
        else {
            checks.push({
                check: "HTTP",
                status: "fail",
                details: `HTTP ${code}`,
            });
        }
    }
    catch {
        checks.push({
            check: "HTTP",
            status: "fail",
            details: "HTTP check failed",
        });
    }
    // Summary
    const passed = checks.filter((c) => c.status === "pass").length;
    const failed = checks.filter((c) => c.status === "fail").length;
    const warned = checks.filter((c) => c.status === "warn").length;
    const total = checks.filter((c) => c.status !== "skip").length;
    const overall = failed > 0 ? "FAIL" : warned > 0 ? "WARN" : "PASS";
    const result = {
        name,
        namespace,
        url: targetUrl,
        overall,
        summary: `${passed}/${total} checks passed`,
        checks,
    };
    return {
        content: [{
                type: "text",
                text: JSON.stringify(result, null, 2),
            }],
    };
}
//# sourceMappingURL=check-health.js.map