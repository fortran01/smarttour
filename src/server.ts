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
import fetch from 'node-fetch';
import { config } from 'dotenv';

// Load environment variables
config();

const API_KEY = process.env.TOMTOM_API_KEY;
if (!API_KEY) {
  console.error('Please set TOMTOM_API_KEY in your .env file');
  process.exit(1);
}

// Define TomTom API response type
interface RouteResponse {
  routes: Array<{
    summary: {
      lengthInMeters: number;
      travelTimeInSeconds: number;
      trafficDelayInSeconds: number;
    };
  }>;
}

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

// Helper function to parse coordinates
const parseCoordinates = (input: string | { lat: number; lon: number }): { lat: number; lon: number } => {
  if (typeof input === 'string') {
    const [lat, lon] = input.split(',').map(Number);
    if (isNaN(lat) || isNaN(lon)) {
      throw new Error('Invalid coordinate format. Expected "lat,lon" or {lat: number, lon: number}');
    }
    return { lat, lon };
  }
  return input;
};

// New schema for the routing tool
const CalculateRouteArgsSchema = z.object({
  from: z.union([
    z.string().regex(/^-?\d+\.?\d*,-?\d+\.?\d*$/),
    z.object({
      lat: z.number(),
      lon: z.number(),
    })
  ]),
  to: z.union([
    z.string().regex(/^-?\d+\.?\d*,-?\d+\.?\d*$/),
    z.object({
      lat: z.number(),
      lon: z.number(),
    })
  ]),
  departAt: z.string().optional(),
  arriveAt: z.string().optional(),
}).strict().refine(
  data => !(data.departAt && data.arriveAt),
  { message: "Cannot specify both departAt and arriveAt" }
).refine(
  data => {
    const timeRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/;
    if (data.departAt && !timeRegex.test(data.departAt)) {
      return false;
    }
    if (data.arriveAt && !timeRegex.test(data.arriveAt)) {
      return false;
    }
    return true;
  },
  { message: "Time must be in format YYYY-MM-DDThh:mm:ss" }
);

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
      },
      {
        name: "calculate_route",
        description:
          "Calculates the route between two points, returning distance, travel time, and traffic delay. Optionally accepts departAt OR arriveAt time in YYYY-MM-DDThh:mm:ss format.",
        inputSchema: zodToJsonSchema(CalculateRouteArgsSchema),
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
      case "calculate_route": {
        const parsed = CalculateRouteArgsSchema.safeParse(args);
        if (!parsed.success) {
          throw new Error(`Invalid arguments for calculate_route: ${parsed.error}`);
        }

        const fromCoords = parseCoordinates(parsed.data.from);
        const toCoords = parseCoordinates(parsed.data.to);
        const { departAt, arriveAt } = parsed.data;

        // Build TomTom API URL
        const baseUrl = 'https://api.tomtom.com/routing/1/calculateRoute';
        const locations = `${fromCoords.lat},${fromCoords.lon}:${toCoords.lat},${toCoords.lon}`;
        const url = new URL(`${baseUrl}/${locations}/json`);

        // Add query parameters
        const params: Record<string, string> = {
          key: API_KEY,
          routeType: 'fastest',
          traffic: 'true',
          travelMode: 'car',
          avoid: 'unpavedRoads',
          sectionType: 'traffic',
          report: 'effectiveSettings',
          computeTravelTimeFor: 'all'
        };

        if (departAt) params.departAt = departAt;
        if (arriveAt) params.arriveAt = arriveAt;

        Object.entries(params).forEach(([key, value]) => {
          url.searchParams.append(key, value);
        });

        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`TomTom API error! status: ${response.status}`);
        }

        const data = await response.json() as RouteResponse;
        
        if (!data.routes?.[0]?.summary) {
          throw new Error('No route found in response');
        }

        const summary = data.routes[0].summary;
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              distanceKm: (summary.lengthInMeters / 1000).toFixed(2),
              travelTimeMinutes: Math.round(summary.travelTimeInSeconds / 60),
              trafficDelayMinutes: Math.round(summary.trafficDelayInSeconds / 60)
            }, null, 2)
          }],
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