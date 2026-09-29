#!/usr/bin/env node
/**
 * Model Context Protocol (MCP) Standard Server for Filesystem.
 * Powered by Node.js native built-in `node:fs` and `node:path`.
 * Supports JSON-RPC 2.0 stdio transport.
 */

const readline = require('node:readline');
const path = require('node:path');
const fs = require('node:fs');

const os = require('node:os');

const args = process.argv.slice(2);
let defaultDocs = path.join(os.homedir(), 'Documents');
let allowedDir = args[0] || defaultDocs;

if (allowedDir.startsWith('~')) {
  allowedDir = path.join(os.homedir(), allowedDir.slice(1));
}

if (!path.isAbsolute(allowedDir)) {
  allowedDir = path.resolve(process.cwd(), allowedDir);
}

if (!fs.existsSync(allowedDir)) {
  try { fs.mkdirSync(allowedDir, { recursive: true }); } catch (e) {}
}

const TOOLS = [
  {
    name: "read_file",
    description: "Read the complete contents of a file as a string",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string", description: "The path of the file to read" }
      },
      required: ["path"]
    }
  },
  {
    name: "write_file",
    description: "Create a new file or completely overwrite an existing file with new content",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string", description: "The path of the file to write" },
        content: { type: "string", description: "The content to write into the file" }
      },
      required: ["path", "content"]
    }
  },
  {
    name: "list_directory",
    description: "Get a detailed list of all files and directories in a specified path",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string", description: "The path of the directory to list" }
      },
      required: ["path"]
    }
  },
  {
    name: "get_file_info",
    description: "Retrieve metadata about a file or directory (size, modified time, type)",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string", description: "The path of the file or directory to inspect" }
      },
      required: ["path"]
    }
  }
];

function resolvePath(filePath) {
  if (path.isAbsolute(filePath)) {
    return filePath;
  }
  return path.resolve(allowedDir, filePath);
}

function handleToolCall(name, toolArgs) {
  try {
    if (name === "read_file") {
      const target = resolvePath(toolArgs.path);
      if (!fs.existsSync(target)) {
        return { isError: true, content: [{ type: "text", text: `File not found: ${target}` }] };
      }
      const data = fs.readFileSync(target, "utf-8");
      return { content: [{ type: "text", text: data }] };
    }

    if (name === "write_file") {
      const target = resolvePath(toolArgs.path);
      const dir = path.dirname(target);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      fs.writeFileSync(target, toolArgs.content || "", "utf-8");
      return { content: [{ type: "text", text: `Successfully wrote ${Buffer.byteLength(toolArgs.content || '', 'utf-8')} bytes to ${target}` }] };
    }

    if (name === "list_directory") {
      const target = resolvePath(toolArgs.path || ".");
      if (!fs.existsSync(target)) {
        return { isError: true, content: [{ type: "text", text: `Directory not found: ${target}` }] };
      }
      const entries = fs.readdirSync(target, { withFileTypes: true });
      const items = entries.map(e => ({
        name: e.name,
        type: e.isDirectory() ? "directory" : "file"
      }));
      return { content: [{ type: "text", text: JSON.stringify(items, null, 2) }] };
    }

    if (name === "get_file_info") {
      const target = resolvePath(toolArgs.path);
      if (!fs.existsSync(target)) {
        return { isError: true, content: [{ type: "text", text: `File or directory not found: ${target}` }] };
      }
      const stats = fs.statSync(target);
      const info = {
        path: target,
        size: stats.size,
        isDirectory: stats.isDirectory(),
        isFile: stats.isFile(),
        modified: stats.mtime.toISOString(),
        created: stats.birthtime.toISOString()
      };
      return { content: [{ type: "text", text: JSON.stringify(info, null, 2) }] };
    }

    return {
      isError: true,
      content: [{ type: "text", text: `Unknown tool: ${name}` }]
    };
  } catch (err) {
    return {
      isError: true,
      content: [{ type: "text", text: `Execution error: ${err.message}` }]
    };
  }
}

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

rl.on('line', (line) => {
  const trimmed = line.trim();
  if (!trimmed) return;

  let msg;
  try {
    msg = JSON.parse(trimmed);
  } catch (e) {
    return;
  }

  // Handle Notifications (no ID)
  if (msg.id === undefined || msg.id === null) {
    return;
  }

  const { id, method, params } = msg;

  if (method === "initialize") {
    const response = {
      jsonrpc: "2.0",
      id,
      result: {
        protocolVersion: "2024-11-05",
        capabilities: {
          tools: { listChanged: false }
        },
        serverInfo: {
          name: "mcp-server-filesystem",
          version: "1.0.0"
        }
      }
    };
    process.stdout.write(JSON.stringify(response) + "\n");
    return;
  }

  if (method === "tools/list") {
    const response = {
      jsonrpc: "2.0",
      id,
      result: {
        tools: TOOLS
      }
    };
    process.stdout.write(JSON.stringify(response) + "\n");
    return;
  }

  if (method === "tools/call") {
    const toolName = params ? params.name : "";
    const toolArgs = params ? (params.arguments || {}) : {};
    const res = handleToolCall(toolName, toolArgs);
    const response = {
      jsonrpc: "2.0",
      id,
      result: res
    };
    process.stdout.write(JSON.stringify(response) + "\n");
    return;
  }

  // Default unsupported method response
  const response = {
    jsonrpc: "2.0",
    id,
    error: {
      code: -32601,
      message: `Method '${method}' not found`
    }
  };
  process.stdout.write(JSON.stringify(response) + "\n");
});
