/**
 * get_deployment_pattern tool
 *
 * Returns deployment patterns and templates for different app types
 */

import { z } from "zod";
import { listTemplates, getTemplateInfo, getProxmoxRoot } from "../clients/registry.js";

export const getDeploymentPatternSchema = {
  appType: z.string().describe("Type of application (e.g., 'python-api', 'frontend', 'database', 'helm')"),
};

interface DeploymentPattern {
  template: string | null;
  pattern: string;
  steps: string[];
  scripts: string[];
  notes: string[];
}

const PATTERNS: Record<string, DeploymentPattern> = {
  "python-api": {
    template: "backend-app",
    pattern: "GitOps with ArgoCD",
    steps: [
      "1. Create Gitea repository from backend-app template",
      "2. Customize Dockerfile for Python app",
      "3. Build container image with Kaniko",
      "4. Create ArgoCD Application",
      "5. Add DNS entry",
      "6. Verify deployment",
    ],
    scripts: [
      "scripts/deploy-app-gitea.sh <app-name>",
      "~/.claude/skills/build-image/scripts/build.sh <app-name>",
    ],
    notes: [
      "Use existing Postgres in gitea namespace if database needed",
      "Default port is 8000, customize in values.yaml",
      "Health endpoint should be at /health",
    ],
  },
  "frontend": {
    template: "frontend-app",
    pattern: "GitOps with ArgoCD",
    steps: [
      "1. Create Gitea repository from frontend-app template",
      "2. Build static assets (npm run build)",
      "3. Create nginx-based Docker image",
      "4. Build with Kaniko",
      "5. Create ArgoCD Application",
      "6. Add DNS entry",
    ],
    scripts: [
      "scripts/deploy-app-gitea.sh <app-name>",
    ],
    notes: [
      "Use nginx to serve static files",
      "Configure nginx.conf for SPA routing if needed",
    ],
  },
  "database": {
    template: null,
    pattern: "Shared or Dedicated",
    steps: [
      "1. Check if existing Postgres can be used (gitea namespace)",
      "2. If shared: Create database in existing instance",
      "3. If dedicated: Deploy PostgreSQL Helm chart",
      "4. Create secrets for credentials",
      "5. Update app to use database connection",
    ],
    scripts: [],
    notes: [
      "Prefer shared Postgres to reduce resource usage",
      "Use dedicated instance only for isolation requirements",
      "Store credentials in Kubernetes secrets",
    ],
  },
  "helm": {
    template: null,
    pattern: "ArgoCD with Helm",
    steps: [
      "1. Add Helm repository if external chart",
      "2. Create values.yaml with customizations",
      "3. Create ArgoCD Application pointing to chart",
      "4. Configure ingress in values",
      "5. Add DNS entry",
    ],
    scripts: [
      "scripts/create-argocd-app.sh <app-name>",
      "scripts/add-dns.sh <app-name>",
    ],
    notes: [
      "ArgoCD manages Helm releases, don't use helm install",
      "Store values.yaml in Gitea repo for version control",
    ],
  },
  "basic": {
    template: "basic-app",
    pattern: "GitOps with ArgoCD",
    steps: [
      "1. Create Gitea repository from basic-app template",
      "2. Customize manifests (deployment.yaml, service.yaml, ingress.yaml)",
      "3. Create ArgoCD Application",
      "4. Add DNS entry",
    ],
    scripts: [
      "scripts/deploy-app-gitea.sh <app-name>",
    ],
    notes: [
      "Good for simple apps without Helm",
      "Raw Kubernetes manifests",
    ],
  },
};

export async function getDeploymentPattern(params: {
  appType: string;
}): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const { appType } = params;
  const normalizedType = appType.toLowerCase().replace(/[_\s]/g, "-");

  // Try to find matching pattern
  let pattern = PATTERNS[normalizedType];

  // Try partial matches
  if (!pattern) {
    for (const [key, value] of Object.entries(PATTERNS)) {
      if (normalizedType.includes(key) || key.includes(normalizedType)) {
        pattern = value;
        break;
      }
    }
  }

  // Default to basic if no match
  if (!pattern) {
    pattern = PATTERNS["basic"];
  }

  // Get template info if available
  let templateInfo = null;
  if (pattern.template) {
    templateInfo = getTemplateInfo(pattern.template);
  }

  // List all available templates
  const availableTemplates = listTemplates();

  const result = {
    requestedType: appType,
    pattern: pattern.pattern,
    template: pattern.template
      ? {
          name: pattern.template,
          path: `${getProxmoxRoot()}/templates/${pattern.template}`,
          exists: templateInfo?.exists || false,
        }
      : null,
    steps: pattern.steps,
    scripts: pattern.scripts,
    notes: pattern.notes,
    availableTemplates,
    commonPaths: {
      templates: `${getProxmoxRoot()}/templates/`,
      scripts: `${getProxmoxRoot()}/scripts/`,
      skills: "~/.claude/skills/",
    },
  };

  return {
    content: [{
      type: "text",
      text: JSON.stringify(result, null, 2),
    }],
  };
}
