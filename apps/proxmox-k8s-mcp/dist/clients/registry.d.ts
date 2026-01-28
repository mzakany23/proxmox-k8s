/**
 * App Registry client
 *
 * Reads and manages the apps.json registry file
 */
export interface AppEntry {
    name: string;
    namespace: string;
    type: string;
    repo?: string;
    url?: string;
    description?: string;
    dependencies?: string[];
}
export interface AppRegistry {
    apps: AppEntry[];
    lastUpdated?: string;
}
/**
 * Read the app registry
 */
export declare function readRegistry(): AppRegistry;
/**
 * Write to the app registry
 */
export declare function writeRegistry(registry: AppRegistry): void;
/**
 * Get a specific app from registry
 */
export declare function getApp(name: string): AppEntry | undefined;
/**
 * Add or update an app in registry
 */
export declare function upsertApp(app: AppEntry): void;
/**
 * List available templates
 */
export declare function listTemplates(): string[];
/**
 * Get template info
 */
export declare function getTemplateInfo(name: string): {
    exists: boolean;
    path: string;
    files: string[];
};
/**
 * Read CLAUDE.md for architecture info
 */
export declare function readClaudeMd(): string;
/**
 * Get proxmox root path
 */
export declare function getProxmoxRoot(): string;
/**
 * Read .env file for tokens
 */
export declare function readEnvVar(varName: string): string | undefined;
//# sourceMappingURL=registry.d.ts.map