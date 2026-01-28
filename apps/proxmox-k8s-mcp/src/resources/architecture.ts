/**
 * architecture://overview resource
 *
 * Returns architecture overview extracted from CLAUDE.md
 */

import { readClaudeMd } from "../clients/registry.js";

export async function getArchitectureOverview(): Promise<string> {
  const claudeMd = readClaudeMd();

  if (!claudeMd) {
    return "# Architecture Overview\n\nCLAUDE.md not found. Please check the repository structure.";
  }

  // Extract key sections from CLAUDE.md
  const sections: string[] = [];

  // Extract Architecture Overview section
  const archMatch = claudeMd.match(/## Architecture Overview[\s\S]*?(?=##\s|$)/);
  if (archMatch) {
    sections.push(archMatch[0].trim());
  }

  // Extract Key Architecture Patterns
  const patternsMatch = claudeMd.match(/### Key Architecture Patterns[\s\S]*?(?=###\s|##\s|$)/);
  if (patternsMatch) {
    sections.push(patternsMatch[0].trim());
  }

  // Extract Important Conventions
  const conventionsMatch = claudeMd.match(/## Important Conventions[\s\S]*?(?=##\s|$)/);
  if (conventionsMatch) {
    sections.push(conventionsMatch[0].trim());
  }

  // Extract Credentials section
  const credsMatch = claudeMd.match(/### Credentials[\s\S]*?(?=###\s|##\s|$)/);
  if (credsMatch) {
    sections.push(credsMatch[0].trim());
  }

  // Extract Power Cycle Recovery
  const powerMatch = claudeMd.match(/## Power Cycle Recovery[\s\S]*?(?=##\s|$)/);
  if (powerMatch) {
    sections.push(powerMatch[0].trim());
  }

  if (sections.length === 0) {
    // Return full CLAUDE.md if no sections extracted
    return claudeMd;
  }

  // Add header and combine
  const output = `# Architecture Overview

*Extracted from CLAUDE.md*

---

${sections.join("\n\n---\n\n")}

---

## Quick Reference

### Key URLs
- ArgoCD: https://argocd.home.mcztest.com
- Gitea: https://gitea.home.mcztest.com
- Grafana: https://grafana.mcztest.com
- Registry: https://registry.home.mcztest.com

### Key IPs
- Ingress Controller: 192.168.68.101
- Gitea SSH: 192.168.68.100

### Namespaces
- \`apps\`: User applications
- \`argocd\`: GitOps engine
- \`gitea\`: Git server + shared Postgres
- \`monitoring\`: Prometheus + Grafana
- \`cert-manager\`: TLS certificates
- \`ingress-nginx\`: Ingress controller

### Deployment Workflow
1. Create repo in Gitea
2. Add Kubernetes manifests or Helm chart
3. Create ArgoCD Application
4. Add DNS entry
5. ArgoCD syncs automatically
`;

  return output;
}
