#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { zodToJsonSchema } from "zod-to-json-schema";
import fs from 'fs';
import path from 'path';

// List of available attractions
const AVAILABLE_ATTRACTIONS = [
  "cn_tower",
  "art_gallery_of_ontario", 
  "casa_loma",
  "distillery_historic_district",
  "hockey_hall_of_fame",
  "little_canada",
  "ripley's_aquarium_of_canada",
  "royal_ontario_museum",
  "st._lawrence_market",
  "toronto_zoo"
] as const;

// Define schemas using Zod
const ReadFileArgsSchema = z.object({}).strict();

const GetAttractionDataArgsSchema = z.object({
  attraction: z.enum(AVAILABLE_ATTRACTIONS)
}).strict();

// Create MCP server instance
const server = new Server(
  {
    name: "SmartTour",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {
        listChanged: true,
      },
    },
  }
);

// Set up request handlers
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "say_hello",
        description:
          "A simple hello world tool that requires no input and always returns 'Hello World!'",
        inputSchema: zodToJsonSchema(ReadFileArgsSchema),
      },
      {
        name: "get_attraction_data",
        description: 
          "Returns data about a specific Toronto attraction including venue info, busy hours, and analysis",
        inputSchema: zodToJsonSchema(GetAttractionDataArgsSchema),
      }
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    const { name, arguments: args } = request.params;
    switch (name) {
      case "say_hello": {
        const parsed = ReadFileArgsSchema.safeParse(args);
        if (!parsed.success) {
          throw new Error(`Invalid arguments for say_hello: ${parsed.error}`);
        }
        return {
          content: [{ type: "text", text: "Hello World!" }],
        };
      }
      case "get_attraction_data": {
        const parsed = GetAttractionDataArgsSchema.safeParse(args);
        if (!parsed.success) {
          throw new Error(`Invalid arguments for get_attraction_data: ${parsed.error}`);
        }
        
        const filePath = path.join(process.cwd(), 'data', `${parsed.data.attraction}.json`);
        const fileContent = fs.readFileSync(filePath, 'utf-8');
        const attractionData = JSON.parse(fileContent);
        
        return {
          content: [{ type: "text", text: JSON.stringify(attractionData, null, 2) }],
        };
      }
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text", text: `Error: ${errorMessage}` }],
      isError: true,
    };
  }
});

// Start server
async function runServer() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("SmartTour MCP Server running on stdio");
}

runServer().catch((error) => {
  console.error("Fatal error running server:", error);
  process.exit(1);
}); 