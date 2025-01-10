# SmartTour

SmartTour is a proof-of-concept application that optimizes tourist itineraries by combining real-time crowd data from BestTime.app and traffic information from TomTom Traffic Stats. The goal is to help tourists maximize their sightseeing experience by minimizing time spent in queues and traffic.

## Solution Overview

SmartTour creates intelligent itineraries by:

1. Analyzing real-time and historical crowd levels at attractions
2. Incorporating traffic patterns between locations
3. Generating optimized visit sequences and timing recommendations

## Features

### Core Features (MVP)

- [ ] MCP server implementation for data source integration
- [ ] Historical data connectors for BestTime.app and TomTom Traffic Stats
- [ ] Claude-powered itinerary optimization engine
- [ ] Support for major Toronto attractions (initial test case)
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

### User Interface

- [ ] Claude-generated itinerary recommendations

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
   bun run src/scripts/prefetchAttractions.ts
   ```

This will:

- Fetch foot traffic forecasts for all Toronto attractions
- Store individual attraction data in `data/{attraction_name}.json`
- Create a combined dataset in `data/all_attractions.json`
