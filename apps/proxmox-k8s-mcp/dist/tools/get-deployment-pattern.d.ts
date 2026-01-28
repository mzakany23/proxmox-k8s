/**
 * get_deployment_pattern tool
 *
 * Returns deployment patterns and templates for different app types
 */
import { z } from "zod";
export declare const getDeploymentPatternSchema: {
    appType: z.ZodString;
};
export declare function getDeploymentPattern(params: {
    appType: string;
}): Promise<{
    content: Array<{
        type: "text";
        text: string;
    }>;
}>;
//# sourceMappingURL=get-deployment-pattern.d.ts.map