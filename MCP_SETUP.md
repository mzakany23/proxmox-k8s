# MCP Server Setup

This repository can be configured as an MCP (Model Context Protocol) server to provide context about your Proxmox Kubernetes homelab setup to AI assistants like Claude.

## What This Provides

When configured as an MCP server, AI assistants can:
- Read all documentation files (READMEs, guides)
- Access templates and example configurations
- Help you with infrastructure setup and troubleshooting
- Reference your specific setup when answering questions

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

- "How do I deploy a new app using the Gitea workflow?"
- "What's the command to add DNS entries?"
- "Show me the ingress configuration for automatic HTTPS"
- "How do I troubleshoot ArgoCD sync issues?"
- "What templates are available?"

Claude will reference your actual setup and documentation when answering.

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
