/**
 * list_services tool
 *
 * Lists all deployed services in the cluster by combining:
 * - apps.json registry (catalog)
 * - kubectl live status
 */
import { z } from "zod";
export declare const listServicesSchema: {
    namespace: z.ZodOptional<z.ZodString>;
    includeSystem: z.ZodOptional<z.ZodBoolean>;
};
export declare function listServices(params: {
    namespace?: string;
    includeSystem?: boolean;
}): Promise<{
    content: Array<{
        type: "text";
        text: string;
    }>;
}>;
//# sourceMappingURL=list-services.d.ts.map