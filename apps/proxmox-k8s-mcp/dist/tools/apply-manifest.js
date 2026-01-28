/**
 * apply_manifest tool
 *
 * Minimal execution tool - just wraps kubectl apply.
 * Used by infra-executor after a plan has been approved.
 */
import { z } from "zod";
import { applyManifest as kubectlApply } from "../clients/kubernetes.js";
export const applyManifestSchema = {
    manifest: z.string().describe("YAML manifest to apply"),
    dryRun: z.boolean().optional().describe("If true, only validate without applying"),
};
export async function applyManifest(params) {
    const { manifest, dryRun = false } = params;
    try {
        // Validate manifest has required fields
        if (!manifest.includes("apiVersion") || !manifest.includes("kind")) {
            return {
                content: [{
                        type: "text",
                        text: JSON.stringify({
                            success: false,
                            error: "Invalid manifest: missing apiVersion or kind",
                        }, null, 2),
                    }],
            };
        }
        if (dryRun) {
            // Dry run - validate only
            const { execSync } = await import("child_process");
            try {
                execSync(`kubectl apply --dry-run=client -f -`, {
                    input: manifest,
                    encoding: "utf-8",
                    stdio: ["pipe", "pipe", "pipe"],
                });
                return {
                    content: [{
                            type: "text",
                            text: JSON.stringify({
                                success: true,
                                dryRun: true,
                                message: "Manifest is valid",
                            }, null, 2),
                        }],
                };
            }
            catch (error) {
                return {
                    content: [{
                            type: "text",
                            text: JSON.stringify({
                                success: false,
                                dryRun: true,
                                error: error.message,
                            }, null, 2),
                        }],
                };
            }
        }
        // Apply the manifest
        const output = kubectlApply(manifest);
        return {
            content: [{
                    type: "text",
                    text: JSON.stringify({
                        success: true,
                        output,
                    }, null, 2),
                }],
        };
    }
    catch (error) {
        return {
            content: [{
                    type: "text",
                    text: JSON.stringify({
                        success: false,
                        error: error.message,
                    }, null, 2),
                }],
        };
    }
}
//# sourceMappingURL=apply-manifest.js.map