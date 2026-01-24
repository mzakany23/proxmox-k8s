/**
 * check_health tool
 *
 * Comprehensive health check for a deployed service
 */
import { z } from "zod";
export declare const checkHealthSchema: {
    name: z.ZodString;
    namespace: z.ZodOptional<z.ZodString>;
    url: z.ZodOptional<z.ZodString>;
};
export declare function checkHealth(params: {
    name: string;
    namespace?: string;
    url?: string;
}): Promise<{
    content: Array<{
        type: "text";
        text: string;
    }>;
}>;
//# sourceMappingURL=check-health.d.ts.map