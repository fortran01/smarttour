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

#### Using the Model

```python
from cpm.model import TourOptimizer

# Initialize the optimizer
optimizer = TourOptimizer(
    venues=["CN Tower", "Casa Loma", "Royal Ontario Museum"],
    dwell_times={
        "CN Tower": 3.0,          # hours
        "Casa Loma": 3.0,
        "Royal Ontario Museum": 3.5
    },
    time_slots=["09:00", "09:30", ...],  # 30-min intervals
    travel_times={
        ("CN Tower", "Casa Loma", "10:00"): 20,  # minutes
        ...
    },
    crowd_levels={
        ("CN Tower", "10:00"): 50,  # crowd intensity
        ...
    },
    tour_start_time="09:00",
    tour_end_time="21:00"
)

# Solve and get the optimized itinerary
solution = optimizer.solve()

if solution:
    print("Selected venues:", solution["selected_venues"])
    print("Start times:", solution["start_times"])
    print("Schedule:", solution["schedule"])
    print("Metrics:", solution["metrics"])
```

The solution includes:
- List of selected venues in visit order
- Start time for each venue
- Detailed schedule with timing and crowd levels
- Optimization metrics (travel time, crowds, etc.)

### Viewing Claude Desktop MCP Logs

To monitor MCP logs from Claude Desktop:

```bash
tail -n 20 -f ~/Library/Logs/Claude/mcp*.log
```
