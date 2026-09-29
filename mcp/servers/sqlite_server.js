#!/usr/bin/env node
/**
 * Model Context Protocol (MCP) Standard Server for SQLite.
 * Powered by Node.js native built-in `node:sqlite` (DatabaseSync).
 * Supports JSON-RPC 2.0 stdio transport.
 */

const readline = require('node:readline');
const path = require('node:path');
const fs = require('node:fs');
const { DatabaseSync } = require('node:sqlite');

const args = process.argv.slice(2);
let dbPath = args[0] || 'knowledge/agent_memory.db';

if (!path.isAbsolute(dbPath)) {
  dbPath = path.resolve(process.cwd(), dbPath);
}

// Ensure directory exists
const dbDir = path.dirname(dbPath);
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}

let db;
try {
  db = new DatabaseSync(dbPath);
} catch (err) {
  console.error(`[sqlite_server] Failed to open DB at ${dbPath}: ${err.message}`);
  process.exit(1);
}

const TOOLS = [
  {
    name: "read_query",
    description: "Execute a SELECT query against the SQLite database and retrieve rows",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "The SQL SELECT statement to execute" }
      },
      required: ["query"]
    }
  },
  {
    name: "write_query",
    description: "Execute an INSERT, UPDATE, or DELETE query against the SQLite database",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "The SQL modification statement to execute" }
      },
      required: ["query"]
    }
  },
  {
    name: "list_tables",
    description: "List all user tables existing in the SQLite database",
    inputSchema: {
      type: "object",
      properties: {}
    }
  },
  {
    name: "describe_table",
    description: "Inspect schema information and column definitions of a specific table",
    inputSchema: {
      type: "object",
      properties: {
        table_name: { type: "string", description: "The table name to inspect" }
      },
      required: ["table_name"]
    }
  }
];

function handleToolCall(name, args) {
  try {
    if (name === "list_tables") {
      const stmt = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;");
      const rows = stmt.all();
      return {
        content: [{ type: "text", text: JSON.stringify(rows, null, 2) }]
      };
    }

    if (name === "describe_table") {
      const tableName = args.table_name || args.tableName;
      if (!tableName) {
        return { isError: true, content: [{ type: "text", text: "Error: table_name required" }] };
      }
      const stmt = db.prepare(`PRAGMA table_info("${tableName.replace(/"/g, '""')}");`);
      const rows = stmt.all();
      return {
        content: [{ type: "text", text: JSON.stringify(rows, null, 2) }]
      };
    }

    if (name === "read_query") {
      const sql = args.query;
      if (!sql) {
        return { isError: true, content: [{ type: "text", text: "Error: query parameter required" }] };
      }
      const stmt = db.prepare(sql);
      const rows = stmt.all();
      return {
        content: [{ type: "text", text: JSON.stringify(rows, null, 2) }]
      };
    }

    if (name === "write_query") {
      const sql = args.query;
      if (!sql) {
        return { isError: true, content: [{ type: "text", text: "Error: query parameter required" }] };
      }
      const stmt = db.prepare(sql);
      const result = stmt.run();
      return {
        content: [{ type: "text", text: JSON.stringify({ changes: result.changes, lastInsertRowid: Number(result.lastInsertRowid) }, null, 2) }]
      };
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
          name: "mcp-server-sqlite",
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
