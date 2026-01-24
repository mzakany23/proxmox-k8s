/**
 * App Registry client
 *
 * Reads and manages the apps.json registry file
 */
import { readFileSync, writeFileSync, existsSync, readdirSync } from "fs";
import { join } from "path";
// Path to the app registry
const REGISTRY_PATH = "/Users/michaelzakany/projects/proxmox/kubernetes/apps/app-registry/apps.json";
const PROXMOX_ROOT = "/Users/michaelzakany/projects/proxmox";
/**
 * Read the app registry
 */
export function readRegistry() {
    try {
        if (!existsSync(REGISTRY_PATH)) {
            return { apps: [] };
        }
        const content = readFileSync(REGISTRY_PATH, "utf-8");
        return JSON.parse(content);
    }
    catch (error) {
        console.error(`Error reading registry: ${error.message}`);
        return { apps: [] };
    }
}
/**
 * Write to the app registry
 */
export function writeRegistry(registry) {
    registry.lastUpdated = new Date().toISOString();
    writeFileSync(REGISTRY_PATH, JSON.stringify(registry, null, 2));
}
/**
 * Get a specific app from registry
 */
export function getApp(name) {
    const registry = readRegistry();
    return registry.apps.find((app) => app.name === name);
}
/**
 * Add or update an app in registry
 */
export function upsertApp(app) {
    const registry = readRegistry();
    const index = registry.apps.findIndex((a) => a.name === app.name);
    if (index >= 0) {
        registry.apps[index] = app;
    }
    else {
        registry.apps.push(app);
    }
    writeRegistry(registry);
}
/**
 * List available templates
 */
export function listTemplates() {
    const templatesDir = join(PROXMOX_ROOT, "templates");
    try {
        const entries = readdirSync(templatesDir, { withFileTypes: true });
        return entries
            .filter((entry) => entry.isDirectory())
            .map((entry) => entry.name);
    }
    catch {
        return [];
    }
}
/**
 * Get template info
 */
export function getTemplateInfo(name) {
    const templatePath = join(PROXMOX_ROOT, "templates", name);
    try {
        if (!existsSync(templatePath)) {
            return { exists: false, path: templatePath, files: [] };
        }
        const files = readdirSync(templatePath, { recursive: true });
        return { exists: true, path: templatePath, files };
    }
    catch {
        return { exists: false, path: templatePath, files: [] };
    }
}
/**
 * Read CLAUDE.md for architecture info
 */
export function readClaudeMd() {
    const claudePath = join(PROXMOX_ROOT, "CLAUDE.md");
    try {
        return readFileSync(claudePath, "utf-8");
    }
    catch {
        return "";
    }
}
/**
 * Get proxmox root path
 */
export function getProxmoxRoot() {
    return PROXMOX_ROOT;
}
/**
 * Read .env file for tokens
 */
export function readEnvVar(varName) {
    const envPath = join(PROXMOX_ROOT, ".env");
    try {
        const content = readFileSync(envPath, "utf-8");
        const match = content.match(new RegExp(`^${varName}=(.*)$`, "m"));
        return match ? match[1] : undefined;
    }
    catch {
        return undefined;
    }
}
//# sourceMappingURL=registry.js.map