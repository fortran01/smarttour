import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

interface Venue {
  venue_id: string;
  venue_name: string;
  venue_address: string;
  venue_forecasted: boolean;
  forecast_updated_on: string;
}

async function fetchVenues() {
  try {
    const apiKey = process.env.BESTTIME_API_KEY;
    if (!apiKey) {
      throw new Error('BESTTIME_API_KEY is not set in environment variables');
    }

    const url = "https://besttime.app/api/v1/venues";
    const params = {
      api_key_private: apiKey
    };

    console.log('Fetching venues from BestTime.app...');
    const response = await fetch(`${url}?${new URLSearchParams(params)}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const venues = await response.json() as Venue[];
    
    // Debug: Log the raw response
    console.log('Raw API Response:', JSON.stringify(venues, null, 2));
    
    // Type check before proceeding
    if (!Array.isArray(venues)) {
      throw new Error('Invalid response format from API - expected an array');
    }
    
    console.log('Venues fetched successfully!');
    console.log('Number of venues:', venues.length);
    
    if (venues.length === 0) {
      console.log('\nNo venues found in your account.');
      return;
    }
    
    // Print all venues
    console.log('\nAll venues:');
    venues.forEach((venue, index) => {
      console.log(`\n${index + 1}. ${venue.venue_name}`);
      console.log(`   Address: ${venue.venue_address}`);
      console.log(`   Forecasted: ${venue.venue_forecasted ? 'Yes' : 'No'}`);
      console.log(`   Last Updated: ${venue.forecast_updated_on}`);
      console.log(`   ID: ${venue.venue_id}`);
    });

  } catch (error) {
    console.error('Error fetching venues:', error);
    if (error instanceof Error) {
      console.error('Error details:', error.message);
    }
    process.exit(1);
  }
}

// Execute the fetch
fetchVenues(); 