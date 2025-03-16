# SmartTour

- [SmartTour](#smarttour)
  - [Solution Overview](#solution-overview)
  - [Features](#features)
    - [Core Features (MVP)](#core-features-mvp)
    - [User Interface](#user-interface)
    - [Limitations](#limitations)
  - [Tech Stack](#tech-stack)
  - [Development](#development)
    - [Prefetching Attraction Data](#prefetching-attraction-data)
      - [Why Prefetch?](#why-prefetch)
      - [How to Prefetch](#how-to-prefetch)
    - [Testing Venue Data](#testing-venue-data)
    - [Testing Routes with Timing](#testing-routes-with-timing)
    - [Running in MCP Inspector](#running-in-mcp-inspector)
    - [Running in Claude Desktop MCP](#running-in-claude-desktop-mcp)
    - [Fetching Timed Routes](#fetching-timed-routes)
      - [How it works](#how-it-works)
      - [Running the script](#running-the-script)
    - [Constraint Programming Model](#constraint-programming-model)
      - [Model Architecture Diagram](#model-architecture-diagram)
      - [Testing the Model](#testing-the-model)
      - [Sample Optimization Run](#sample-optimization-run)
      - [Pareto Optimality Analysis](#pareto-optimality-analysis)
    - [Viewing Claude Desktop MCP Logs](#viewing-claude-desktop-mcp-logs)
    - [Scripts Overview](#scripts-overview)
      - [`fetchTimedRoutes.ts`](#fetchtimedroutests)
      - [`prefetchAttractions.ts`](#prefetchattractionsts)
      - [`testRouting.ts`](#testroutingts)
      - [`testVenueFetching.ts`](#testvenuefetchingts)


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

### Fetching Timed Routes

The `fetchTimedRoutes.ts` script generates comprehensive route timing data between attractions, taking into account:
- Venue operating hours
- Required dwell times at each venue
- Real-time traffic conditions
- Time-based routing for different days of the week

#### How it works

1. Loads venue data and operating schedules for all attractions
2. Reads minimum dwell times from `venue_dwell_times.csv`
3. Calculates routes between venue pairs for each day of the week
4. Generates time slots at 30-minute intervals during overlapping operating hours
5. Validates routes based on:
   - Sufficient time to spend at the origin venue
   - Adequate remaining time at the destination venue
   - Real-time traffic conditions
6. Saves results to `data/timed_routes.csv`

#### Running the script

```bash
# Set up your TomTom API key in .env:
TOMTOM_API_KEY=your_api_key_here

# Run the timed routes fetcher:
bun run fetch:routes
```

The script will:
- Process routes for all days of the week
- Calculate bi-directional routes between all venue pairs
- Skip existing routes to avoid duplicate API calls
- Display progress and validation information
- Save results in CSV format with:
  - Day and time of departure
  - Origin and destination venues
  - Distance in kilometers
  - Travel time in minutes
  - Traffic delay in minutes

### Constraint Programming Model

The project uses a constraint programming model (implemented in `src/cpm/model.py`) to optimize tour itineraries, with data loading handled by `src/cpm/data_loader.py`. The system:

1. **Data Loading and Processing**:
   - Loads venue data from individual JSON files
   - Processes operating hours with support for multiple open/close intervals per day
   - Handles dwell times from `venue_dwell_times.csv`
   - Manages travel times with intelligent time slot matching
   - Extracts and normalizes crowd levels from venue data

2. **Optimizes for Multiple Objectives**:
   - Minimizes total travel time between venues
   - Minimizes exposure to crowds
   - Maximizes the number of venues visited

3. **Handles Key Constraints**:
   - Venue operating hours with support for multiple open/close periods
   - Required dwell times at each venue
   - Travel times between venues (with traffic)
   - No overlapping visits
   - Sequential visit ordering

4. **Input Data Structure**:
   - Individual venue JSON files with operating hours and crowd data
   - `venue_dwell_times.csv` for required visit durations
   - `timed_routes.csv` for travel times between venues
   - Time slots in 30-minute intervals
   - Day-specific operating hours and crowd levels

#### Model Architecture Diagram

[![](https://mermaid.ink/img/pako:eNp1U1FvmzAQ_iuW-7JJlEESB4KmSlXTTnvYVq1dH1b24MLRWDU2MiZZGuW_72ySlCKNB-T7fJ-_z3fnHS10CTSjldSbYsWNJffLXBH8CsnbdgkVEarp7JWLSCWkzM4grlgFQWuNfoHsLIpZsngakRqjC2jbIa2aAqvYiTbj8SwtRjTd2bFYWjFYnFjxE4NJlKue99VZe_yQU78gS2755ydzcU4eQHXQ9usfDSihnslKd-YAXRm9KYmENcgDcm84BsSKGtqcfvxDzs8vkImxeAWz2-X0HulvSE73-97DrYEKDCi87mNOf7VghlB_-p11lXWH9_G1KgfRkm-JrsgG4CWnI-Veo_-fQJ_ys5Ne8bJppIC2jzN3YhyS75qsXQmIXoORvHHwJCQ3WmKfiR5XZBqSS79j38rg8FnorG_JRtiVUB7GtSr1Bo0OrXlxb-uL5tLZOprFPmpztPUgWmFJrQ2QRvJDedDXN6F88ljf-VprUZLCNawdiXopL3pXrKBEC6h7ZYBbVD1CI84R7qvspw1JN0JxSXyHbyVXh7kxJTYRx0S01vVnPZgp39BPcGjj-xkSCoe1K6zQauzYz3k_tYNnNdwbjM5_Mk5TEPiiB30Vhu_tXba_YnC69uCB0YDWYGouSnz_O0fKqV1BjSXLcFlCxTtpc5qrPabyzuq7rSpohpeDgHZNiXVeCv5seE2zCk0g2nD1W-v6mIQhzXb0L83ieRSyJEojlrAZmy_maUC3NJum4YzFLJpOWJKmcboP6KvnR-EinsxZMk_SeJJM0jQ9Sl6XwmpzUjS6e14dov0_JauZfA?type=png)](https://mermaid.live/edit#pako:eNp1U1FvmzAQ_iuW-7JJlEESB4KmSlXTTnvYVq1dH1b24MLRWDU2MiZZGuW_72ySlCKNB-T7fJ-_z3fnHS10CTSjldSbYsWNJffLXBH8CsnbdgkVEarp7JWLSCWkzM4grlgFQWuNfoHsLIpZsngakRqjC2jbIa2aAqvYiTbj8SwtRjTd2bFYWjFYnFjxE4NJlKue99VZe_yQU78gS2755ydzcU4eQHXQ9usfDSihnslKd-YAXRm9KYmENcgDcm84BsSKGtqcfvxDzs8vkImxeAWz2-X0HulvSE73-97DrYEKDCi87mNOf7VghlB_-p11lXWH9_G1KgfRkm-JrsgG4CWnI-Veo_-fQJ_ys5Ne8bJppIC2jzN3YhyS75qsXQmIXoORvHHwJCQ3WmKfiR5XZBqSS79j38rg8FnorG_JRtiVUB7GtSr1Bo0OrXlxb-uL5tLZOprFPmpztPUgWmFJrQ2QRvJDedDXN6F88ljf-VprUZLCNawdiXopL3pXrKBEC6h7ZYBbVD1CI84R7qvspw1JN0JxSXyHbyVXh7kxJTYRx0S01vVnPZgp39BPcGjj-xkSCoe1K6zQauzYz3k_tYNnNdwbjM5_Mk5TEPiiB30Vhu_tXba_YnC69uCB0YDWYGouSnz_O0fKqV1BjSXLcFlCxTtpc5qrPabyzuq7rSpohpeDgHZNiXVeCv5seE2zCk0g2nD1W-v6mIQhzXb0L83ieRSyJEojlrAZmy_maUC3NJum4YzFLJpOWJKmcboP6KvnR-EinsxZMk_SeJJM0jQ9Sl6XwmpzUjS6e14dov0_JauZfA)

#### Testing the Model

To run the test suite for the constraint programming model:

```bash
# Ensure you're in the project root
cd /path/to/smarttour

# Set up Python environment if not already done
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run the tests
PYTHONPATH=. pytest src/cpm/test_cpm.py -v
```

The test suite includes:
- Basic model initialization
- Solving a simple tour with 3 venues
- Time window constraint validation
- Travel time constraint validation

Example test output:
```
test_basic_initialization PASSED
test_solve_basic_tour PASSED
test_time_window_constraints PASSED
test_travel_time_constraints PASSED
```

#### Sample Optimization Run

To run the tour optimizer with the sample data:

```bash
python -m src.cpm.optimize_tour
```

Here's an example output showing an optimized Tuesday itinerary for three major Toronto attractions:

```
Optimized Tour Schedule:
==================================================

Casa Loma:
  Start time: 10:00
  End time: 13:00
  Duration: 3.0 hours
  Crowd level: -0.3
  Travel to next venue: 11 min

Royal Ontario Museum:
  Start time: 13:30
  End time: 17:00
  Duration: 3.5 hours
  Crowd level: 1.0
  Travel to next venue: 17 min

CN Tower:
  Start time: 17:30
  End time: 20:30
  Duration: 3.0 hours
  Crowd level: -0.3

Tour Metrics:
==================================================
Total venues visited: 3
Total travel time: 28 minutes
Average travel time: 14.0 minutes
Average crowd level: 0.1
```

The optimizer has created an efficient schedule that:
1. Starts at Casa Loma during its quieter morning hours
2. Visits the Royal Ontario Museum during mid-afternoon
3. Ends at the CN Tower for evening views of the city
4. Minimizes both travel time (28 minutes total) and crowd exposure (0.1 average level)
5. Respects each venue's operating hours and required visit durations
6. Allows sufficient time for travel between venues

Crowd levels are on a scale from -2 (very quiet) to +2 (very busy), with 0 representing average crowds.

#### Pareto Optimality Analysis

The Pareto Optimality Analysis helps understand the trade-offs between competing objectives in the tour optimization problem:

1. Minimizing total travel time between venues
2. Minimizing exposure to crowds at venues
3. Maximizing the number of venues visited

The analysis generates multiple solutions by systematically varying the weights in the objective function and identifies the Pareto-optimal (non-dominated) solutions. A solution is Pareto-optimal if no other solution is better in all objectives.

**Running the Analysis:**

```bash
# Run with default settings (Tuesday, 5 points per weight)
python -m src.cpm.run_pareto_analysis

# Run with custom settings
python -m src.cpm.run_pareto_analysis --day Friday --points 3 --output pareto_results_friday
```

**Outputs:**

- 3D visualization of the Pareto front showing the trade-offs between all three objectives
- 2D visualizations showing pairwise trade-offs between objectives
- CSV file with all solutions and their metrics

**Interpreting the Results:**

The Pareto front represents the set of solutions where improving one objective necessarily degrades at least one other objective. This analysis helps decision-makers understand the trade-offs and choose a solution that best matches their preferences.

For example, if minimizing crowd exposure is more important than visiting many venues, a solution from the appropriate region of the Pareto front can be selected.

**Implementation Details:**

- `src/cpm/pareto_analysis.py`: Core implementation of the Pareto analysis
- `src/cpm/run_pareto_analysis.py`: Command-line interface for running the analysis

### Viewing Claude Desktop MCP Logs

To monitor MCP logs from Claude Desktop:

```bash
tail -n 20 -f ~/Library/Logs/Claude/mcp*.log
```

### Scripts Overview

The project includes several utility scripts in `src/scripts/` for data collection and testing:

#### `fetchTimedRoutes.ts`

A comprehensive route timing data generator that:
- Calculates routes between all venue pairs for each day of the week
- Takes into account venue operating hours and required dwell times
- Generates time slots at 30-minute intervals during overlapping operating hours
- Validates routes based on:
  - Sufficient time to spend at origin venue
  - Adequate remaining time at destination venue
  - Real-time traffic conditions
- Saves results to `data/timed_routes.csv`

Usage:
```bash
# Set up your TomTom API key in .env:
TOMTOM_API_KEY=your_api_key_here

# Run the timed routes fetcher:
bun run fetch:routes
```

#### `prefetchAttractions.ts`

Prefetches and caches foot traffic data for Toronto attractions using BestTime.app's API:
- Fetches forecasts for 10 major Toronto attractions
- Saves individual attraction data to `data/{attraction_name}.json`
- Creates a combined dataset in `data/all_attractions.json`
- Implements rate limiting and error handling
- Saves API credits by caching predictions

Usage:
```bash
# Set up your BestTime.app API key in .env:
BESTTIME_API_KEY=your_api_key_here

# Run the prefetch script:
bun run prefetch
```

#### `testRouting.ts`

Tests the TomTom Routing API functionality with various timing options:
- Calculates routes between CN Tower and Casa Loma (both directions)
- Supports departure and arrival time specifications
- Saves detailed route data to `data/routes/`
- Provides route summaries with:
  - Distance in kilometers
  - Travel time in minutes
  - Traffic delay information

Usage:
```bash
# Set up your TomTom API key in .env:
TOMTOM_API_KEY=your_api_key_here

# Test with current traffic conditions:
bun run test:routes

# Test with specific departure time:
bun run test:routes --depart-at 2024-01-20T09:00:00

# Test with specific arrival time:
bun run test:routes --arrive-at 2024-01-20T17:30:00

# Show usage information:
bun run test:routes --help
```

#### `testVenueFetching.ts`

Tests the BestTime.app Venues API functionality:
- Retrieves all venues in your BestTime.app account
- Displays detailed venue information:
  - Venue name and address
  - Forecasting status
  - Last forecast update time
  - Venue ID
- Useful for verifying venue data and API integration

Usage:
```bash
# Set up your BestTime.app API key in .env:
BESTTIME_API_KEY=your_api_key_here

# Run the venue test:
bun run test:venues
```