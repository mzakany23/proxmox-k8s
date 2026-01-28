/**
 * get_service_info tool
 *
 * Get detailed information about a specific service
 */
import { z } from "zod";
export declare const getServiceInfoSchema: {
    name: z.ZodString;
    namespace: z.ZodOptional<z.ZodString>;
};
export declare function getServiceInfo(params: {
    name: string;
    namespace?: string;
}): Promise<{
    content: Array<{
        type: "text";
        text: string;
    }>;
}>;
//# sourceMappingURL=get-service-info.d.ts.map