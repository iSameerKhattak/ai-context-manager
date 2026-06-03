import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const server = new Server(
  { name: "contextclaw-mcp", version: "0.1.0" },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "search_context",
      description: "Search indexed project context",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string", description: "Search query" },
          project_id: { type: "string", description: "Project ID" },
          k: { type: "number", description: "Number of results (1-50)" },
        },
        required: ["query", "project_id"],
      },
    },
    {
      name: "get_memory_facts",
      description: "Get asserted memory facts for a project",
      inputSchema: {
        type: "object",
        properties: {
          project_id: { type: "string", description: "Project ID" },
          scope: {
            type: "string",
            enum: ["org", "project", "repo", "user"],
          },
        },
        required: ["project_id"],
      },
    },
    {
      name: "remember_fact",
      description: "Assert a persistent fact about the project",
      inputSchema: {
        type: "object",
        properties: {
          project_id: { type: "string", description: "Project ID" },
          statement: {
            type: "string",
            description: "The fact to remember",
          },
        },
        required: ["project_id", "statement"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case "search_context":
      return {
        content: [
          {
            type: "text",
            text: `Searching for "${args?.query}" in project ${args?.project_id}`,
          },
        ],
      };
    case "get_memory_facts":
      return {
        content: [
          {
            type: "text",
            text: `Memory facts for project ${args?.project_id}: ...`,
          },
        ],
      };
    case "remember_fact":
      return {
        content: [
          {
            type: "text",
            text: `Remembered: "${args?.statement}"`,
          },
        ],
      };
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
