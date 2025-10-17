# MCP Server Setup

This repository can be configured as an MCP (Model Context Protocol) server to provide context about your Proxmox Kubernetes homelab setup to AI assistants like Claude.

## What This Provides

When configured as an MCP server, AI assistants can:
- Read all documentation files (READMEs, guides)
- Access templates and example configurations
- Help you with infrastructure setup and troubleshooting
- Reference your specific setup when answering questions
- Guide you through app deployments using the deployment scripts
- Help troubleshoot ArgoCD GitOps workflows
- Explain Let's Encrypt certificate configuration
- Provide kubectl commands for your specific cluster setup

## Quick Setup for Claude Desktop

1. **Find your Claude Desktop config file:**

   **macOS:**
   ```bash
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```

   **Windows:**
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   ```

   **Linux:**
   ```bash
   ~/.config/Claude/claude_desktop_config.json
   ```

2. **Add this MCP server configuration:**

   Edit the config file and add this entry to the `mcpServers` object:

   ```json
   {
     "mcpServers": {
       "proxmox-k8s-homelab": {
         "command": "npx",
         "args": [
           "-y",
           "@modelcontextprotocol/server-filesystem",
           "/Users/michaelzakany/projects/proxmox"
         ]
       }
     }
   }
   ```

   **Important:** Replace `/Users/michaelzakany/projects/proxmox` with your actual repo path!

3. **Restart Claude Desktop**

   The MCP server will be available in Claude Desktop after restart.

## Alternative: Use Included Config File

You can copy the included `mcp-server.json` configuration:

```bash
# macOS
cat mcp-server.json >> ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Or manually merge the contents
```

**Remember to update the path** in `mcp-server.json` to your actual repo location before copying!

## Verify It's Working

After setup, in Claude Desktop:
1. Start a new conversation
2. Look for the MCP indicator (usually a small icon or badge)
3. Ask Claude: "What documentation do you have access to for my homelab?"

Claude should be able to see and reference:
- Main README with quick start guide
- Scripts documentation (`scripts/README.md`)
- Templates guide (`templates/README.md`)
- Infrastructure component READMEs (ArgoCD, cert-manager, Gitea)
- All Kubernetes manifests and configurations

## Example Usage

Once configured, you can ask Claude:

- "How do I deploy a new app with HTTPS to my Proxmox cluster?"
- "Show me how to use the deploy-app.sh script"
- "What's my cluster architecture and network setup?"
- "How do I troubleshoot ArgoCD sync issues?"
- "Walk me through pushing infrastructure changes to Gitea"
- "What templates are available for frontend vs backend apps?"
- "How is Let's Encrypt configured with Cloudflare DNS-01?"
- "Show me the GitOps workflow from code change to deployment"

Claude will reference your actual setup and documentation when answering.

## Key Information Available to AI

The MCP server provides access to:
- **Deployment Scripts**: `./scripts/deploy-app.sh` for app deployments
- **Templates**: Frontend (with HTTPS ingress) and backend (internal) app templates
- **GitOps Config**: ArgoCD Application watching `kubernetes/infrastructure` in Gitea
- **Infrastructure Manifests**: MetalLB, Ingress, cert-manager, ArgoCD configurations
- **Network Details**: LoadBalancer pool 192.168.68.100-110, domain configuration
- **Terraform Setup**: VM provisioning and k3s cluster configuration

## Advanced: Custom Tools and Prompts

The filesystem MCP server provides read-only access to your repo. For more advanced features, you could create a custom MCP server with:

- **Tools** to execute deployment scripts
- **Prompts** for common setup tasks
- **Resources** for structured data

See [MCP Documentation](https://modelcontextprotocol.io) for creating custom servers.

## Troubleshooting

**"MCP server not showing up":**
- Ensure the path in the config is absolute and correct
- Check that `npx` is available in your PATH
- Restart Claude Desktop completely

**"Permission denied":**
- Make sure Claude has read access to the repo directory
- On macOS, you may need to grant Full Disk Access to Claude in System Preferences

**"Server keeps disconnecting":**
- Check the Claude Desktop logs (Help → View Logs)
- Ensure `@modelcontextprotocol/server-filesystem` can be installed via npx

## Security Note

The filesystem MCP server gives Claude **read-only** access to this directory and all subdirectories. It cannot:
- Modify or delete files
- Execute commands
- Access files outside this directory

However, it can read:
- All markdown documentation
- Kubernetes manifests (including any secrets in plain text)
- Scripts and configuration files

**Do not commit sensitive data** (API tokens, passwords) to this repo if using it as an MCP server.
