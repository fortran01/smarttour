import { config } from 'dotenv';
import fetch from 'node-fetch';
import { writeFile } from 'fs/promises';
import { join } from 'path';

// Load environment variables
config();

const API_KEY = process.env.BESTTIME_API_KEY;
if (!API_KEY) {
  console.error('Please set BESTTIME_API_KEY in your .env file');
  process.exit(1);
}

interface Venue {
  name: string;
  address: string;
}

interface ForecastResult {
  name: string;
  data: any;
}

const attractions: Venue[] = [
  {
    name: 'CN Tower',
    address: '290 Bremner Blvd, Toronto, ON M5V 3L9, Canada'
  },
  {
    name: 'Royal Ontario Museum',
    address: '100 Queens Park, Toronto, ON M5S 2C6, Canada'
  },
  {
    name: 'Casa Loma',
    address: '1 Austin Terrace, Toronto, ON M5R 1X8, Canada'
  },
  {
    name: "Ripley's Aquarium of Canada",
    address: '288 Bremner Blvd, Toronto, ON M5V 3L9, Canada'
  },
  {
    name: 'Distillery Historic District',
    address: '55 Mill St, Toronto, ON M5A 3C4, Canada'
  },
  {
    name: 'Art Gallery of Ontario',
    address: '317 Dundas St W, Toronto, ON M5T 1G4, Canada'
  },
  {
    name: 'Hockey Hall of Fame',
    address: '30 Yonge St, Toronto, ON M5E 1X8, Canada'
  },
  {
    name: 'St. Lawrence Market',
    address: '93 Front St E, Toronto, ON M5E 1C3, Canada'
  },
  {
    name: 'Toronto Zoo',
    address: '2000 Meadowvale Rd, Toronto, ON M1B 5K7, Canada'
  },
  {
    name: 'Little Canada',
    address: '10 Dundas St E, Toronto, ON M5B 2G9, Canada'
  }
];

async function fetchForecast(venue: Venue): Promise<ForecastResult | null> {
  const url = 'https://besttime.app/api/v1/forecasts';
  const params = new URLSearchParams({
    'api_key_private': API_KEY as string,
    'venue_name': venue.name,
    'venue_address': venue.address
  });

  try {
    const requestUrl = `${url}?${params}`;
    console.log(`Making request to: ${requestUrl}`);
    
    const response = await fetch(requestUrl, {
      method: 'POST'
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`HTTP error! status: ${response.status}, body: ${errorText}`);
      return null;
    }
    
    const responseText = await response.text();
    console.log(`Raw response for ${venue.name}:`, responseText);
    
    try {
      const data = JSON.parse(responseText);
      if (data.status === 'OK') {
        console.log(`Successfully fetched data for ${venue.name}`);
        return {
          name: venue.name,
          data
        };
      } else {
        console.error(`API error for ${venue.name}:`, data.message || 'Unknown error');
        return null;
      }
    } catch (parseError) {
      console.error(`Error parsing JSON for ${venue.name}:`, parseError);
      console.error('Response text was:', responseText);
      return null;
    }
  } catch (error) {
    console.error(`Network error fetching data for ${venue.name}:`, error);
    return null;
  }
}

async function main() {
  console.log('Starting to fetch forecasts for Toronto attractions...');
  
  // Create data directory if it doesn't exist
  const dataDir = join(process.cwd(), 'data');
  try {
    await writeFile(join(dataDir, '.gitkeep'), '');
  } catch (error) {
    // Directory might already exist, continue
  }

  const results: ForecastResult[] = [];
  for (const attraction of attractions) {
    console.log(`\nFetching forecast for ${attraction.name}...`);
    const result = await fetchForecast(attraction);
    if (result) {
      results.push(result);
      // Save individual attraction data
      await writeFile(
        join(dataDir, `${attraction.name.toLowerCase().replace(/\s+/g, '_')}.json`),
        JSON.stringify(result.data, null, 2)
      );
      console.log(`Successfully saved data for ${attraction.name}`);
    }
    // Wait 2 seconds between requests to avoid rate limiting
    console.log('Waiting 2 seconds before next request...');
    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  if (results.length > 0) {
    // Save all results in one file
    await writeFile(
      join(dataDir, 'all_attractions.json'),
      JSON.stringify(results, null, 2)
    );
    console.log('\nSaved combined results to all_attractions.json');
  } else {
    console.error('\nNo successful results were obtained');
  }

  console.log('\nFinished fetching forecasts!');
}

main().catch(console.error); 