#!/usr/bin/env node
/**
 * Model Context Protocol (MCP) Standard Server for Fetch.
 * Powered by Node.js native built-in `fetch`.
 * Supports JSON-RPC 2.0 stdio transport.
 */

const readline = require('node:readline');

const TOOLS = [
  {
    name: "fetch",
    description: "Fetches content from a URL via HTTP/HTTPS and returns plain text or markdown",
    inputSchema: {
      type: "object",
      properties: {
        url: { type: "string", description: "The URL to fetch" },
        max_length: { type: "integer", description: "Maximum characters to return (default: 8000)" }
      },
      required: ["url"]
    }
  },
  {
    name: "read_url",
    description: "Fetches web page content and converts HTML to readable markdown text",
    inputSchema: {
      type: "object",
      properties: {
        url: { type: "string", description: "The URL to fetch and convert" }
      },
      required: ["url"]
    }
  }
];

function htmlToMarkdown(html) {
  // Strip scripts and styles
  let clean = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "");
  clean = clean.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, "");
  // Simple markdown conversion
  clean = clean.replace(/<h1[^>]*>(.*?)<\/h1>/gi, "\n# $1\n");
  clean = clean.replace(/<h2[^>]*>(.*?)<\/h2>/gi, "\n## $1\n");
  clean = clean.replace(/<h3[^>]*>(.*?)<\/h3>/gi, "\n### $1\n");
  clean = clean.replace(/<p[^>]*>(.*?)<\/p>/gi, "\n$1\n");
  clean = clean.replace(/<br\s*[\/]?>/gi, "\n");
  clean = clean.replace(/<li[^>]*>(.*?)<\/li>/gi, "\n* $1");
  clean = clean.replace(/<a[^>]*href="([^"]*)"[^>]*>(.*?)<\/a>/gi, "[$2]($1)");
  clean = clean.replace(/<[^>]+>/g, "");
  // Unescape common HTML entities
  clean = clean.replace(/&amp;/g, "&")
               .replace(/&lt;/g, "<")
               .replace(/&gt;/g, ">")
               .replace(/&quot;/g, "\"")
               .replace(/&#39;/g, "'")
               .replace(/&nbsp;/g, " ");
  return clean.replace(/\n\s*\n\s*\n/g, "\n\n").trim();
}

async function handleToolCall(name, args) {
  try {
    const url = args.url;
    if (!url) {
      return { isError: true, content: [{ type: "text", text: "Error: url argument required" }] };
    }

    const res = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OrvixSphere/1.0"
      }
    });

    if (!res.ok) {
      return {
        isError: true,
        content: [{ type: "text", text: `HTTP error ${res.status}: ${res.statusText}` }]
      };
    }

    const text = await res.text();
    const formatted = htmlToMarkdown(text);
    const maxLen = args.max_length || 8000;
    const truncated = formatted.length > maxLen ? formatted.slice(0, maxLen) + "\n...[truncated]" : formatted;

    return {
      content: [{ type: "text", text: truncated }]
    };
  } catch (err) {
    return {
      isError: true,
      content: [{ type: "text", text: `Fetch error: ${err.message}` }]
    };
  }
}

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

rl.on('line', async (line) => {
  const trimmed = line.trim();
  if (!trimmed) return;

  let msg;
  try {
    msg = JSON.parse(trimmed);
  } catch (e) {
    return;
  }

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
          name: "mcp-server-fetch",
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
    const res = await handleToolCall(toolName, toolArgs);
    const response = {
      jsonrpc: "2.0",
      id,
      result: res
    };
    process.stdout.write(JSON.stringify(response) + "\n");
    return;
  }

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
