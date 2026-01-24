/**
 * Kubernetes client wrapper
 *
 * Executes kubectl commands and parses output
 */
export interface PodInfo {
    name: string;
    namespace: string;
    status: string;
    ready: string;
    restarts: number;
    age: string;
}
export interface ServiceInfo {
    name: string;
    namespace: string;
    type: string;
    clusterIP: string;
    externalIP: string;
    ports: string;
}
export interface IngressInfo {
    name: string;
    namespace: string;
    hosts: string[];
    address: string;
}
export interface ApplicationInfo {
    name: string;
    namespace: string;
    syncStatus: string;
    healthStatus: string;
    repo: string;
}
/**
 * Execute kubectl command and return output
 */
export declare function kubectl(args: string, options?: {
    json?: boolean;
}): string;
/**
 * Get pods in a namespace
 */
export declare function getPods(namespace?: string): PodInfo[];
/**
 * Get services in a namespace
 */
export declare function getServices(namespace?: string): ServiceInfo[];
/**
 * Get ingresses in a namespace
 */
export declare function getIngresses(namespace?: string): IngressInfo[];
/**
 * Get ArgoCD applications
 */
export declare function getApplications(): ApplicationInfo[];
/**
 * Describe a resource
 */
export declare function describe(resource: string, name: string, namespace: string): string;
/**
 * Get events for a namespace
 */
export declare function getEvents(namespace: string, limit?: number): string;
/**
 * Check if a resource exists
 */
export declare function resourceExists(resource: string, name: string, namespace: string): boolean;
/**
 * Apply a manifest from stdin
 */
export declare function applyManifest(manifest: string): string;
//# sourceMappingURL=kubernetes.d.ts.map