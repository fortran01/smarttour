# SmartTour

SmartTour is a proof-of-concept application that optimizes tourist itineraries by combining real-time crowd data from BestTime.app and traffic information from TomTom Traffic Stats. The goal is to help tourists maximize their sightseeing experience by minimizing time spent in queues and traffic.

## Solution Overview

SmartTour creates intelligent itineraries by:

1. Analyzing real-time and historical crowd levels at attractions
2. Incorporating traffic patterns between locations
3. Generating optimized visit sequences and timing recommendations

## Features

### Core Features (MVP)

- [x] MCP server implementation for historical data source integration with BestTime.app
- [x] MCP server implementation for real-time data source integration with TomTom Traffic Stats
- [x] Claude-powered itinerary optimization engine
- [x] Support for major Toronto attractions (initial test case)
- [x] Prefetch Toronto attractions using BestTime.app's New Foot Traffic Forecast API endpoint (`/api/v1/forecasts`):
  - CN Tower
  - Royal Ontario Museum (ROM)
  - Casa Loma
  - Ripley's Aquarium of Canada
  - Distillery Historic District
  - Art Gallery of Ontario (AGO)
  - Hockey Hall of Fame
  - St. Lawrence Market
  - Toronto Zoo
  - Little Canada
- [x] Test venue fetching using BestTime.app's Venues API endpoint (`/api/v1/venues`)

### User Interface

- [x] Claude-generated itinerary recommendations

### Limitations

- No access to TomTom Traffic Stats API, so we'll use TomTom's Routing API to get traffic data. Not sure if the Routing API accounts for historical traffic data.

## Tech Stack

- TypeScript for type-safe development
- MCP server for data source integration

## Development

### Prefetching Attraction Data

The project uses a data prefetching strategy to optimize API usage and response times when working with BestTime.app's foot traffic data. Here's why and how:

#### Why Prefetch?

When using BestTime.app's API endpoints for new foot-traffic data, the generated predictions are stored on your account for several days. Instead of generating fresh predictions on every request (which costs 2 API credits), we can query existing data (costing only 1 API credit) when the data is still valid.

#### How to Prefetch

- Set up your BestTime.app API key in `.env`:

  ```dotenv
  BESTTIME_API_KEY=your_api_key_here
  ```

- Run the prefetch script:

   ```bash
   bun run prefetch
   ```

This will:

- Fetch foot traffic forecasts for all Toronto attractions
- Store individual attraction data in `data/{attraction_name}.json`
- Create a combined dataset in `data/all_attractions.json`

### Testing Venue Data

To view all venues currently in your BestTime.app account:

```bash
bun run test:venues
```

This will display:

- Total number of venues in your account
- For each venue:
  - Name and address
  - Whether it has forecasting enabled
  - Last forecast update time
  - Venue ID

### Testing Routes with Timing

To test routes between attractions with specific timing options:

```bash
# Set up your TomTom API key in .env:
TOMTOM_API_KEY=your_api_key_here

# Run the routing test with different options:
bun run test:routes                                    # Current traffic conditions
bun run test:routes --depart-at 2024-01-20T09:00:00   # Specific departure time
bun run test:routes --arrive-at 2024-01-20T17:30:00   # Specific arrival time
bun run test:routes --help                            # Show usage information
```

The script will:

- Calculate routes between CN Tower and Casa Loma in both directions
- Include real-time traffic information
- Save detailed route data to `data/routes/`
- Display a summary with:
  - Distance in kilometers
  - Estimated travel time
  - Expected traffic delays

### Running in MCP Inspector

To test the MCP server functionality using the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector npx tsx src/server.ts
```

### Running in Claude Desktop MCP

To use SmartTour with Claude Desktop, add the following configuration to your Claude Desktop MCP settings (typically in `~/.claude/mcp-config.json`):

```json
{
  "mcpServers": {
    "smarttour": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "TOMTOM_API_KEY=your_api_key_here",
        "mcp/smarttour"
      ]
    }
  }
}
```

### Viewing Claude Desktop MCP Logs

To monitor MCP logs from Claude Desktop:

```bash
tail -n 20 -f ~/Library/Logs/Claude/mcp*.log
```
