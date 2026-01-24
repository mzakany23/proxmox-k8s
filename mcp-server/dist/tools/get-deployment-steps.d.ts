/**
 * get_deployment_steps tool
 *
 * Returns the steps needed to deploy an application.
 * Read-only - provides a plan, doesn't execute anything.
 * Designed to feed into the planner → executor workflow.
 */
import { z } from "zod";
export declare const getDeploymentStepsSchema: {
    name: z.ZodString;
    template: z.ZodOptional<z.ZodString>;
    namespace: z.ZodOptional<z.ZodString>;
    hasDockerfile: z.ZodOptional<z.ZodBoolean>;
};
export declare function getDeploymentSteps(params: {
    name: string;
    template?: string;
    namespace?: string;
    hasDockerfile?: boolean;
}): Promise<{
    content: Array<{
        type: "text";
        text: string;
    }>;
}>;
//# sourceMappingURL=get-deployment-steps.d.ts.map