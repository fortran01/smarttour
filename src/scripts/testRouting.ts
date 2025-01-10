import { config } from 'dotenv';
import fetch from 'node-fetch';
import { writeFile, readFile, mkdir } from 'fs/promises';
import { join } from 'path';

// Load environment variables
config();

const API_KEY = process.env.TOMTOM_API_KEY;
if (!API_KEY) {
  console.error('Please set TOMTOM_API_KEY in your .env file');
  process.exit(1);
}

interface VenueLocation {
  name: string;
  lat: number;
  lon: number;
}

interface VenueData {
  venue_info: {
    venue_name: string;
    venue_lat: number;
    venue_lon: number;
  };
}

interface RouteResponse {
  routes: Array<{
    summary: {
      lengthInMeters: number;
      travelTimeInSeconds: number;
      trafficDelayInSeconds: number;
    };
  }>;
}

interface RouteOptions {
  departAt?: string;
  arriveAt?: string;
}

function parseArgs(): RouteOptions {
  const args = process.argv.slice(2);
  const options: RouteOptions = {};

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--depart-at':
        options.departAt = args[++i];
        break;
      case '--arrive-at':
        options.arriveAt = args[++i];
        break;
    }
  }

  if (options.departAt && options.arriveAt) {
    console.error('Error: Cannot specify both --depart-at and --arrive-at');
    process.exit(1);
  }

  // Validate time format (YYYY-MM-DDThh:mm:ss)
  const timeRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/;
  if (options.departAt && !timeRegex.test(options.departAt)) {
    console.error('Error: --depart-at must be in format YYYY-MM-DDThh:mm:ss');
    process.exit(1);
  }
  if (options.arriveAt && !timeRegex.test(options.arriveAt)) {
    console.error('Error: --arrive-at must be in format YYYY-MM-DDThh:mm:ss');
    process.exit(1);
  }

  return options;
}

async function loadVenueLocations(): Promise<VenueLocation[]> {
  const venues: VenueLocation[] = [];
  const dataDir = join(process.cwd(), 'data');

  try {
    // Read CN Tower and Casa Loma data as an example
    const cnTowerData = JSON.parse(await readFile(join(dataDir, 'cn_tower.json'), 'utf-8')) as VenueData;
    const casaLomaData = JSON.parse(await readFile(join(dataDir, 'casa_loma.json'), 'utf-8')) as VenueData;

    // Add CN Tower
    venues.push({
      name: cnTowerData.venue_info.venue_name,
      lat: cnTowerData.venue_info.venue_lat,
      lon: cnTowerData.venue_info.venue_lon
    });

    // Add Casa Loma
    venues.push({
      name: casaLomaData.venue_info.venue_name,
      lat: casaLomaData.venue_info.venue_lat,
      lon: casaLomaData.venue_info.venue_lon
    });

    console.log('Loaded venues:', venues.map(v => `${v.name} (${v.lat}, ${v.lon})`));
    return venues;
  } catch (error) {
    console.error('Error loading venue data:', error);
    return [];
  }
}

async function calculateRoute(origin: VenueLocation, destination: VenueLocation, options: RouteOptions = {}) {
  const baseUrl = 'https://api.tomtom.com/routing/1/calculateRoute';
  const locations = `${origin.lat},${origin.lon}:${destination.lat},${destination.lon}`;
  
  // Build URL with common parameters
  const url = new URL(`${baseUrl}/${locations}/json`);
  const params: Record<string, string> = {
    key: API_KEY as string,
    routeType: 'fastest',
    traffic: 'true',
    travelMode: 'car',
    avoid: 'unpavedRoads',
    sectionType: 'traffic',
    report: 'effectiveSettings',
    computeTravelTimeFor: 'all'
  };

  // Add timing parameters if specified
  if (options.departAt) {
    params.departAt = options.departAt;
  }
  if (options.arriveAt) {
    params.arriveAt = options.arriveAt;
  }

  // Add query parameters to URL
  Object.entries(params).forEach(([key, value]) => {
    url.searchParams.append(key, value);
  });

  try {
    console.log(`\nCalculating route from ${origin.name} to ${destination.name}...`);
    console.log(`From: (${origin.lat}, ${origin.lon})`);
    console.log(`To: (${destination.lat}, ${destination.lon})`);
    if (options.departAt) {
      console.log(`Departure Time: ${options.departAt}`);
    }
    if (options.arriveAt) {
      console.log(`Arrival Time: ${options.arriveAt}`);
    }
    console.log(`Request URL: ${url}`);

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json() as RouteResponse;
    
    // Ensure routes directory exists
    const routesDir = join(process.cwd(), 'data', 'routes');
    await mkdir(routesDir, { recursive: true });
    
    // Save route data
    const filename = `${origin.name.toLowerCase().replace(/\s+/g, '_')}_to_${destination.name.toLowerCase().replace(/\s+/g, '_')}.json`;
    await writeFile(
      join(routesDir, filename),
      JSON.stringify(data, null, 2)
    );

    // Log summary
    if (data.routes && data.routes[0]) {
      const route = data.routes[0].summary;
      console.log('\nRoute Summary:');
      console.log(`- Distance: ${(route.lengthInMeters / 1000).toFixed(2)} km`);
      console.log(`- Travel Time: ${Math.round(route.travelTimeInSeconds / 60)} minutes`);
      console.log(`- Traffic Delay: ${Math.round(route.trafficDelayInSeconds / 60)} minutes`);
    }

  } catch (error) {
    console.error(`Error calculating route:`, error);
  }
}

async function main() {
  console.log('Starting TomTom Routing API test...');
  
  // Parse command line arguments
  const options = parseArgs();

  // Create routes directory if it doesn't exist
  const routesDir = join(process.cwd(), 'data', 'routes');
  await mkdir(routesDir, { recursive: true });

  const venues = await loadVenueLocations();
  if (venues.length < 2) {
    console.error('Not enough venues loaded to calculate routes');
    return;
  }

  // Calculate route from CN Tower to Casa Loma with timing options
  await calculateRoute(venues[0], venues[1], options);
  
  // Calculate reverse route (Casa Loma to CN Tower) with timing options
  await calculateRoute(venues[1], venues[0], options);

  console.log('\nFinished calculating routes!');
}

// Print usage if --help is specified
if (process.argv.includes('--help')) {
  console.log(`
Usage: bun run test:routes [options]

Options:
  --depart-at <time>  Specify departure time (format: YYYY-MM-DDThh:mm:ss)
  --arrive-at <time>  Specify arrival time (format: YYYY-MM-DDThh:mm:ss)
  --help              Show this help message

Examples:
  bun run test:routes --depart-at 2024-01-20T09:00:00
  bun run test:routes --arrive-at 2024-01-20T17:30:00
`);
  process.exit(0);
}

main().catch(console.error); 