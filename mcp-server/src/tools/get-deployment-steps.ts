/**
 * get_deployment_steps tool
 *
 * Returns the steps needed to deploy an application.
 * Read-only - provides a plan, doesn't execute anything.
 * Designed to feed into the planner → executor workflow.
 */

import { z } from "zod";
import { existsSync } from "fs";
import { join } from "path";
import { resourceExists } from "../clients/kubernetes.js";
import { getProxmoxRoot, listTemplates, readEnvVar } from "../clients/registry.js";

export const getDeploymentStepsSchema = {
  name: z.string().describe("Name of the application to deploy"),
  template: z.string().optional().describe("Template to use (basic-app, frontend-app, backend-app)"),
  namespace: z.string().optional().describe("Target namespace (default: apps)"),
  hasDockerfile: z.boolean().optional().describe("Whether app has a Dockerfile to build"),
};

interface DeploymentStep {
  order: number;
  name: string;
  description: string;
  command?: string;
  manualAction?: string;
  verification?: string;
  canFail?: boolean;
}

interface PrerequisiteCheck {
  name: string;
  status: "ready" | "missing" | "unknown";
  detail: string;
  resolution?: string;
}

interface DeploymentPlan {
  appName: string;
  template: string;
  namespace: string;
  prerequisites: PrerequisiteCheck[];
  steps: DeploymentStep[];
  estimatedCommands: number;
  rollback: string[];
  notes: string[];
}

export async function getDeploymentSteps(params: {
  name: string;
  template?: string;
  namespace?: string;
  hasDockerfile?: boolean;
}): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const {
    name,
    template = "basic-app",
    namespace = "apps",
    hasDockerfile = false,
  } = params;

  const proxmoxRoot = getProxmoxRoot();
  const plan: DeploymentPlan = {
    appName: name,
    template,
    namespace,
    prerequisites: [],
    steps: [],
    estimatedCommands: 0,
    rollback: [],
    notes: [],
  };

  // Check prerequisites
  // 1. Gitea token
  const giteaToken = readEnvVar("GITEA_API_TOKEN");
  plan.prerequisites.push({
    name: "Gitea API Token",
    status: giteaToken ? "ready" : "missing",
    detail: giteaToken ? "Token found in .env" : "GITEA_API_TOKEN not found",
    resolution: giteaToken ? undefined : "Run gitea-auth skill to create token",
  });

  // 2. Template exists
  const templatePath = join(proxmoxRoot, "templates", template);
  const templateExists = existsSync(templatePath);
  plan.prerequisites.push({
    name: "Template",
    status: templateExists ? "ready" : "missing",
    detail: templateExists ? `Template found: ${template}` : `Template not found: ${template}`,
    resolution: templateExists ? undefined : `Available templates: ${listTemplates().join(", ")}`,
  });

  // 3. App doesn't already exist
  const appExists = resourceExists("application", name, "argocd");
  plan.prerequisites.push({
    name: "App Name Available",
    status: appExists ? "missing" : "ready",
    detail: appExists ? `Application '${name}' already exists in ArgoCD` : "Name is available",
    resolution: appExists ? "Choose a different name or delete existing app first" : undefined,
  });

  // 4. Namespace
  const nsExists = resourceExists("namespace", namespace, "");
  plan.prerequisites.push({
    name: "Namespace",
    status: "ready", // ArgoCD will create if needed
    detail: nsExists ? `Namespace '${namespace}' exists` : `Namespace '${namespace}' will be created`,
  });

  // Build deployment steps
  let stepOrder = 0;

  // Step 1: Create Gitea repository
  plan.steps.push({
    order: ++stepOrder,
    name: "Create Gitea Repository",
    description: "Create a new private repository in Gitea",
    command: `curl -s -X POST "https://gitea.home.mcztest.com/api/v1/user/repos" \\
  -H "Authorization: token \${GITEA_TOKEN}" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "${name}", "private": true}'`,
    verification: "Response should contain 'id' field",
  });

  // Step 2: Clone and customize template
  plan.steps.push({
    order: ++stepOrder,
    name: "Setup from Template",
    description: `Clone ${template} template and customize for ${name}`,
    command: `cp -r ${templatePath} /tmp/${name} && \\
cd /tmp/${name} && \\
find . -type f -exec sed -i '' 's/{{APP_NAME}}/${name}/g' {} \\; 2>/dev/null || true`,
    verification: "Template files copied and customized",
  });

  // Step 3: Initialize git and push
  plan.steps.push({
    order: ++stepOrder,
    name: "Push to Gitea",
    description: "Initialize git repo and push to Gitea",
    command: `cd /tmp/${name} && \\
git init && \\
git add . && \\
git commit -m "Initial commit from ${template} template" && \\
git remote add origin "https://homelab:\${GITEA_TOKEN}@gitea.home.mcztest.com/homelab/${name}.git" && \\
git push -u origin main --force`,
    verification: "Git push succeeds",
  });

  // Step 4: Build image (if Dockerfile)
  if (hasDockerfile) {
    plan.steps.push({
      order: ++stepOrder,
      name: "Build Container Image",
      description: "Build and push container image using Kaniko",
      command: `~/.claude/skills/build-image/scripts/build.sh ${name}`,
      verification: "kubectl logs shows 'Pushed image' message",
    });
  }

  // Step 5: Create ArgoCD Application
  plan.steps.push({
    order: ++stepOrder,
    name: "Create ArgoCD Application",
    description: "Create ArgoCD Application to manage deployment",
    command: `kubectl apply -f - <<'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ${name}
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://gitea.home.mcztest.com/homelab/${name}.git
    targetRevision: main
    path: deploy/helm/${name}
  destination:
    server: https://kubernetes.default.svc
    namespace: ${namespace}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
EOF`,
    verification: "kubectl get application ${name} -n argocd shows 'Synced'",
  });

  // Step 6: Add DNS
  plan.steps.push({
    order: ++stepOrder,
    name: "Add DNS Entry",
    description: "Add Cloudflare DNS entry for the application",
    command: `${proxmoxRoot}/scripts/add-dns.sh ${name} 192.168.68.101`,
    verification: "dig ${name}.mcztest.com returns 192.168.68.101",
    canFail: true,
  });

  // Step 7: Verify deployment
  plan.steps.push({
    order: ++stepOrder,
    name: "Verify Deployment",
    description: "Confirm application is running and accessible",
    command: `kubectl get pods -n ${namespace} -l app=${name} && \\
curl -sk https://${name}.mcztest.com/`,
    verification: "Pods running, HTTP response received",
  });

  plan.estimatedCommands = plan.steps.length;

  // Rollback steps
  plan.rollback = [
    `kubectl delete application ${name} -n argocd`,
    `kubectl delete all,ingress,secret -l app=${name} -n ${namespace}`,
    `# Delete Gitea repo via API or UI`,
    `# Remove DNS entry via Cloudflare`,
  ];

  // Notes
  plan.notes = [
    `URL will be: https://${name}.mcztest.com`,
    "ArgoCD will auto-sync changes pushed to main branch",
    "Certificate will be issued automatically by cert-manager",
  ];

  if (hasDockerfile) {
    plan.notes.push("Container image will be at: registry.home.mcztest.com/" + name);
  }

  // Check if any prerequisites are missing
  const missingPrereqs = plan.prerequisites.filter((p) => p.status === "missing");
  if (missingPrereqs.length > 0) {
    plan.notes.unshift(`⚠️ ${missingPrereqs.length} prerequisite(s) need attention before proceeding`);
  }

  return {
    content: [{
      type: "text",
      text: JSON.stringify(plan, null, 2),
    }],
  };
}
