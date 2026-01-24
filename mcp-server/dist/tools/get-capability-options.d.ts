/**
 * get_capability_options tool
 *
 * Returns information about options for adding a capability.
 * Read-only - provides facts and questions, doesn't execute anything.
 * Designed to feed into the researcher → planner → executor workflow.
 */
import { z } from "zod";
export declare const getCapabilityOptionsSchema: {
    capability: z.ZodEnum<["database", "cache", "queue", "storage", "monitoring", "logging", "auth", "search"]>;
    requirements: z.ZodOptional<z.ZodString>;
};
export declare function getCapabilityOptions(params: {
    capability: string;
    requirements?: string;
}): Promise<{
    content: Array<{
        type: "text";
        text: string;
    }>;
}>;
//# sourceMappingURL=get-capability-options.d.ts.map