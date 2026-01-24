/**
 * apply_manifest tool
 *
 * Minimal execution tool - just wraps kubectl apply.
 * Used by infra-executor after a plan has been approved.
 */
import { z } from "zod";
export declare const applyManifestSchema: {
    manifest: z.ZodString;
    dryRun: z.ZodOptional<z.ZodBoolean>;
};
export declare function applyManifest(params: {
    manifest: string;
    dryRun?: boolean;
}): Promise<{
    content: Array<{
        type: "text";
        text: string;
    }>;
}>;
//# sourceMappingURL=apply-manifest.d.ts.map