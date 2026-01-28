/**
 * Kubernetes client wrapper
 *
 * Executes kubectl commands and parses output
 */
import { execSync } from "child_process";
/**
 * Execute kubectl command and return output
 */
export function kubectl(args, options) {
    try {
        const cmd = options?.json ? `kubectl ${args} -o json` : `kubectl ${args}`;
        return execSync(cmd, {
            encoding: "utf-8",
            timeout: 30000,
            stdio: ["pipe", "pipe", "pipe"],
        }).trim();
    }
    catch (error) {
        throw new Error(`kubectl ${args} failed: ${error.message}`);
    }
}
/**
 * Get pods in a namespace
 */
export function getPods(namespace) {
    const ns = namespace ? `-n ${namespace}` : "-A";
    const output = kubectl(`get pods ${ns} --no-headers`);
    if (!output)
        return [];
    return output.split("\n").map((line) => {
        const parts = line.trim().split(/\s+/);
        if (namespace) {
            // Without namespace column
            const [name, ready, status, restarts, age] = parts;
            return { name, namespace, ready, status, restarts: parseInt(restarts) || 0, age };
        }
        else {
            // With namespace column
            const [ns, name, ready, status, restarts, age] = parts;
            return { name, namespace: ns, ready, status, restarts: parseInt(restarts) || 0, age };
        }
    });
}
/**
 * Get services in a namespace
 */
export function getServices(namespace) {
    const ns = namespace ? `-n ${namespace}` : "-A";
    const output = kubectl(`get svc ${ns} --no-headers`);
    if (!output)
        return [];
    return output.split("\n").map((line) => {
        const parts = line.trim().split(/\s+/);
        if (namespace) {
            const [name, type, clusterIP, externalIP, ports, age] = parts;
            return { name, namespace, type, clusterIP, externalIP, ports };
        }
        else {
            const [ns, name, type, clusterIP, externalIP, ports, age] = parts;
            return { name, namespace: ns, type, clusterIP, externalIP, ports };
        }
    });
}
/**
 * Get ingresses in a namespace
 */
export function getIngresses(namespace) {
    const ns = namespace ? `-n ${namespace}` : "-A";
    const output = kubectl(`get ingress ${ns} --no-headers 2>/dev/null || true`);
    if (!output)
        return [];
    return output.split("\n").filter(Boolean).map((line) => {
        const parts = line.trim().split(/\s+/);
        if (namespace) {
            const [name, className, hosts, address] = parts;
            return { name, namespace, hosts: hosts.split(","), address };
        }
        else {
            const [ns, name, className, hosts, address] = parts;
            return { name, namespace: ns, hosts: hosts.split(","), address };
        }
    });
}
/**
 * Get ArgoCD applications
 */
export function getApplications() {
    try {
        const output = kubectl(`get applications -n argocd --no-headers 2>/dev/null || true`);
        if (!output)
            return [];
        return output.split("\n").filter(Boolean).map((line) => {
            const parts = line.trim().split(/\s+/);
            const [name, syncStatus, healthStatus] = parts;
            return {
                name,
                namespace: "argocd",
                syncStatus,
                healthStatus,
                repo: "", // Would need describe to get this
            };
        });
    }
    catch {
        return [];
    }
}
/**
 * Describe a resource
 */
export function describe(resource, name, namespace) {
    return kubectl(`describe ${resource} ${name} -n ${namespace}`);
}
/**
 * Get events for a namespace
 */
export function getEvents(namespace, limit = 10) {
    return kubectl(`get events -n ${namespace} --sort-by='.lastTimestamp' | tail -${limit}`);
}
/**
 * Check if a resource exists
 */
export function resourceExists(resource, name, namespace) {
    try {
        kubectl(`get ${resource} ${name} -n ${namespace}`);
        return true;
    }
    catch {
        return false;
    }
}
/**
 * Apply a manifest from stdin
 */
export function applyManifest(manifest) {
    try {
        return execSync(`kubectl apply -f -`, {
            input: manifest,
            encoding: "utf-8",
            timeout: 30000,
        }).trim();
    }
    catch (error) {
        throw new Error(`kubectl apply failed: ${error.message}`);
    }
}
//# sourceMappingURL=kubernetes.js.map