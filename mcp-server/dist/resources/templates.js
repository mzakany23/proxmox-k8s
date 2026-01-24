/**
 * templates://catalog resource
 *
 * Returns available deployment templates and their descriptions
 */
import { existsSync, readdirSync, statSync } from "fs";
import { join } from "path";
import { getProxmoxRoot } from "../clients/registry.js";
const TEMPLATE_DESCRIPTIONS = {
    "basic-app": "Simple Kubernetes manifests without Helm. Good for straightforward deployments.",
    "frontend-app": "Frontend application template with nginx serving static files.",
    "backend-app": "Backend API template with Python/FastAPI structure and Helm chart.",
};
export async function getTemplatesCatalog() {
    const templatesDir = join(getProxmoxRoot(), "templates");
    const templates = [];
    if (!existsSync(templatesDir)) {
        return JSON.stringify({ templates: [], error: "Templates directory not found" }, null, 2);
    }
    const templateNames = readdirSync(templatesDir).filter((name) => {
        const path = join(templatesDir, name);
        return statSync(path).isDirectory();
    });
    for (const name of templateNames) {
        const templatePath = join(templatesDir, name);
        // Get files in template
        const files = [];
        const walkDir = (dir, prefix = "") => {
            const entries = readdirSync(dir);
            for (const entry of entries) {
                const fullPath = join(dir, entry);
                const relativePath = prefix ? `${prefix}/${entry}` : entry;
                if (statSync(fullPath).isDirectory()) {
                    walkDir(fullPath, relativePath);
                }
                else {
                    files.push(relativePath);
                }
            }
        };
        try {
            walkDir(templatePath);
        }
        catch {
            // Skip if can't read
        }
        // Check for Helm and Dockerfile
        const hasHelm = files.some((f) => f.includes("Chart.yaml") || f.includes("values.yaml"));
        const hasDockerfile = files.some((f) => f.toLowerCase().includes("dockerfile"));
        templates.push({
            name,
            path: templatePath,
            description: TEMPLATE_DESCRIPTIONS[name] || "No description available",
            files,
            hasHelm,
            hasDockerfile,
        });
    }
    // Also include scripts info
    const scriptsDir = join(getProxmoxRoot(), "scripts");
    const scripts = [];
    if (existsSync(scriptsDir)) {
        const scriptFiles = readdirSync(scriptsDir).filter((f) => f.endsWith(".sh"));
        scripts.push(...scriptFiles);
    }
    const result = {
        timestamp: new Date().toISOString(),
        templatesPath: templatesDir,
        scriptsPath: scriptsDir,
        templates,
        deploymentScripts: scripts.map((s) => ({
            name: s,
            path: join(scriptsDir, s),
        })),
        usage: {
            deployWithTemplate: "deploy_app(name, template)",
            listServices: "list_services()",
            checkHealth: "check_health(name)",
        },
    };
    return JSON.stringify(result, null, 2);
}
//# sourceMappingURL=templates.js.map