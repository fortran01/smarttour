import { config } from 'dotenv';
import fetch from 'node-fetch';
import { writeFile, readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';
import { parse } from 'csv-parse/sync';

// Load environment variables
config();

const API_KEY = process.env.TOMTOM_API_KEY;
if (!API_KEY) {
  console.error('Please set TOMTOM_API_KEY in your .env file');
  process.exit(1);
}

interface VenueData {
  venue_info: {
    venue_name: string;
    venue_lat: number;
    venue_lon: number;
  };
  analysis: Array<{
    day_info: {
      day_int: number;
      day_text: string;
      venue_open_close_v2: {
        "24h": Array<{
          opens: number;
          closes: number;
        }>;
      };
    };
  }>;
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

interface RouteData {
  day: string;
  time: string;
  from: string;
  to: string;
  distanceKm: number;
  travelTimeMinutes: number;
  trafficDelayMinutes: number;
}

interface DaySchedule {
  day_int: number;
  day_text: string;
  opens: number;
  closes: number;
}

interface VenueDwellTime {
  venue: string;
  dwellTimeHours: number;
}

async function loadVenueData(venueName: string): Promise<VenueData> {
  const filePath = join(process.cwd(), 'data', `${venueName}.json`);
  const fileContent = await readFile(filePath, 'utf-8');
  return JSON.parse(fileContent);
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function calculateRoute(
  fromLat: number,
  fromLon: number,
  toLat: number,
  toLon: number,
  departAt: string
): Promise<RouteResponse> {
  const baseUrl = 'https://api.tomtom.com/routing/1/calculateRoute';
  const locations = `${fromLat},${fromLon}:${toLat},${toLon}`;
  const url = new URL(`${baseUrl}/${locations}/json`);

  const params: Record<string, string> = {
    key: API_KEY as string,
    routeType: 'fastest',
    traffic: 'true',
    travelMode: 'car',
    avoid: 'unpavedRoads',
    sectionType: 'traffic',
    report: 'effectiveSettings',
    computeTravelTimeFor: 'all',
    departAt
  };

  Object.entries(params).forEach(([key, value]) => {
    url.searchParams.append(key, value);
  });

  // Add retry logic with exponential backoff
  let retries = 3;
  let lastError: Error | null = null;
  
  while (retries > 0) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return response.json() as Promise<RouteResponse>;
      }
      
      if (response.status === 429) {
        console.log('Rate limit hit, waiting before retry...');
        await delay(5000); // Wait 5 seconds before retry
        retries--;
        continue;
      }
      
      throw new Error(`TomTom API error! status: ${response.status}`);
    } catch (error) {
      lastError = error as Error;
      retries--;
      if (retries > 0) {
        const waitTime = (4 - retries) * 5000; // Exponential backoff
        console.log(`API call failed, retrying in ${waitTime/1000} seconds...`);
        await delay(waitTime);
      }
    }
  }

  throw lastError || new Error('Failed to fetch route after all retries');
}

function getVenueSchedule(venueData: VenueData): DaySchedule[] {
  // Convert day_int from Monday=0 to Sunday=0 format
  const convertDayInt = (mondayBasedDay: number): number => {
    // Convert from Monday=0 to Sunday=0
    return (mondayBasedDay + 6) % 7;
  };

  return venueData.analysis.map(day => {
    // Check if the venue is closed (empty 24h array)
    if (!day.day_info.venue_open_close_v2['24h'] || day.day_info.venue_open_close_v2['24h'].length === 0) {
      return {
        day_int: convertDayInt(day.day_info.day_int),
        day_text: day.day_info.day_text,
        opens: -1,  // Use -1 to indicate closed
        closes: -1  // Use -1 to indicate closed
      };
    }
    
    return {
      day_int: convertDayInt(day.day_info.day_int),
      day_text: day.day_info.day_text,
      opens: day.day_info.venue_open_close_v2['24h'][0].opens,
      closes: day.day_info.venue_open_close_v2['24h'][0].closes
    };
  });
}

function getOverlappingHours(schedule1: DaySchedule, schedule2: DaySchedule): { openTime: number; closeTime: number } | null {
  // If either venue is closed (indicated by -1), return null
  if (schedule1.opens === -1 || schedule1.closes === -1 || 
      schedule2.opens === -1 || schedule2.closes === -1) {
    return null;
  }

  const openTime = Math.max(schedule1.opens, schedule2.opens);
  const closeTime = schedule1.closes;

  return openTime <= closeTime ? { openTime, closeTime } : null;
}

async function loadExistingRoutes(): Promise<RouteData[]> {
  const csvPath = join(process.cwd(), 'data', 'timed_routes.csv');
  if (!existsSync(csvPath)) {
    return [];
  }

  try {
    const content = await readFile(csvPath, 'utf-8');
    const lines = content.split('\n').slice(1); // Skip header
    return lines.filter(line => line.trim()).map(line => {
      const [day, time, from, to, distanceKm, travelTimeMinutes, trafficDelayMinutes] = line.split(',');
      return {
        day,
        time,
        from,
        to,
        distanceKm: Number(distanceKm),
        travelTimeMinutes: Number(travelTimeMinutes),
        trafficDelayMinutes: Number(trafficDelayMinutes)
      };
    });
  } catch (error) {
    console.error('Error loading existing routes:', error);
    return [];
  }
}

async function loadDwellTimes(): Promise<Map<string, number>> {
  const dwellTimesPath = join(process.cwd(), 'data', 'venue_dwell_times.csv');
  const content = await readFile(dwellTimesPath, 'utf-8');
  const records = parse(content, {
    columns: true,
    skip_empty_lines: true
  }) as Array<{ Venue: string; 'Dwell Time (hours)': string }>;

  const dwellTimes = new Map<string, number>();
  records.forEach(record => {
    dwellTimes.set(record.Venue, Number(record['Dwell Time (hours)']));
  });
  return dwellTimes;
}

function getDateForDayOfWeek(targetDayInt: number): string {
  const today = new Date();
  const currentDayInt = today.getDay();
  const daysToAdd = (targetDayInt - currentDayInt + 7) % 7;
  
  const targetDate = new Date(today);
  targetDate.setDate(today.getDate() + daysToAdd);
  
  return targetDate.toISOString().split('T')[0];
}

async function calculateRoutesForVenuePair(
  venue1Data: VenueData,
  venue2Data: VenueData,
  venue1Schedule: DaySchedule,
  venue2Schedule: DaySchedule,
  venue1DwellHours: number,
  venue2DwellHours: number,
  dayText: string,
  existingRouteMap: Map<string, RouteData>
): Promise<RouteData[]> {
  const newRoutes: RouteData[] = [];

  // Calculate routes from venue1 to venue2
  const venue1ToVenue2Hours = getOverlappingHours(venue1Schedule, venue2Schedule);
  if (venue1ToVenue2Hours) {
    // Get the correct date for this day of the week
    const targetDate = getDateForDayOfWeek(venue1Schedule.day_int);

    // Generate timestamps at 30-minute intervals for venue1 to venue2
    for (let hour = venue1ToVenue2Hours.openTime; hour <= venue1ToVenue2Hours.closeTime; hour++) {
      for (let minute of [0, 30]) {
        if (hour === venue1ToVenue2Hours.closeTime && minute > 0) continue;
        
        const timeStr = `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
        const timestamp = `${targetDate}T${timeStr}:00`;

        // Venue1 to Venue2
        if (hour < venue1Schedule.closes || (hour === venue1Schedule.closes && minute === 0)) {
          // Only check time spent at venue1 if we're leaving at closing time
          if (hour === venue1Schedule.closes && minute === 0) {
            const hoursSpentAtVenue1 = hour - venue1Schedule.opens;
            if (hoursSpentAtVenue1 < venue1DwellHours) {
              console.log(`Skipping ${timeStr}: Can't leave at closing time, not enough time spent at ${venue1Data.venue_info.venue_name} (${hoursSpentAtVenue1.toFixed(1)} hours < ${venue1DwellHours} hours needed)`);
              continue;
            }
          }

          // Only check time at destination if it closes earlier than the starting venue
          if (venue2Schedule.closes <= venue1Schedule.closes) {
            // Estimate if there will be enough time at venue2
            const estimatedTravelTime = 30; // minutes
            const estimatedArrivalHour = hour + Math.floor(estimatedTravelTime / 60);
            const estimatedArrivalMinute = minute + (estimatedTravelTime % 60);
            const estimatedHoursUntilClose = venue2Schedule.closes - estimatedArrivalHour - (estimatedArrivalMinute / 60);

            if (estimatedHoursUntilClose < venue2DwellHours) {
              console.log(`Skipping ${timeStr}: Estimated only ${estimatedHoursUntilClose.toFixed(1)} hours available at ${venue2Data.venue_info.venue_name} (need ${venue2DwellHours} hours)`);
              continue;
            }
          }

          const routeKey = `${dayText}-${timeStr}-${venue1Data.venue_info.venue_name}-${venue2Data.venue_info.venue_name}`;
          if (!existingRouteMap.has(routeKey)) {
            console.log(`Fetching route: ${venue1Data.venue_info.venue_name} -> ${venue2Data.venue_info.venue_name} at ${timeStr}`);
            const route = await calculateRoute(
              venue1Data.venue_info.venue_lat,
              venue1Data.venue_info.venue_lon,
              venue2Data.venue_info.venue_lat,
              venue2Data.venue_info.venue_lon,
              timestamp
            );

            if (route.routes?.[0]) {
              const routeSummary = route.routes[0].summary;
              const travelTimeHours = routeSummary.travelTimeInSeconds / 3600;
              const arrivalHour = hour + Math.floor(travelTimeHours);
              const arrivalMinute = minute + Math.round((travelTimeHours % 1) * 60);
              
              // Only check actual time at destination if it closes earlier
              let shouldAddRoute = true;
              if (venue2Schedule.closes <= venue1Schedule.closes) {
                const hoursUntilClose = venue2Schedule.closes - arrivalHour - (arrivalMinute / 60);
                if (hoursUntilClose < venue2DwellHours) {
                  console.log(`Skipping route: Actual time available at ${venue2Data.venue_info.venue_name} (${hoursUntilClose.toFixed(1)} hours) is less than required`);
                  shouldAddRoute = false;
                }
              }
              
              if (shouldAddRoute) {
                newRoutes.push({
                  day: dayText,
                  time: timeStr,
                  from: venue1Data.venue_info.venue_name,
                  to: venue2Data.venue_info.venue_name,
                  distanceKm: Number((routeSummary.lengthInMeters / 1000).toFixed(2)),
                  travelTimeMinutes: Math.round(routeSummary.travelTimeInSeconds / 60),
                  trafficDelayMinutes: Math.round(routeSummary.trafficDelayInSeconds / 60)
                });
              }
            }
          }
        }
      }
    }
  }

  // Calculate routes from venue2 to venue1
  const venue2ToVenue1Hours = getOverlappingHours(venue2Schedule, venue1Schedule);
  if (venue2ToVenue1Hours) {
    // Get the correct date for this day of the week
    const targetDate = getDateForDayOfWeek(venue2Schedule.day_int);

    // Generate timestamps at 30-minute intervals for venue2 to venue1
    for (let hour = venue2ToVenue1Hours.openTime; hour <= venue2ToVenue1Hours.closeTime; hour++) {
      for (let minute of [0, 30]) {
        if (hour === venue2ToVenue1Hours.closeTime && minute > 0) continue;
        
        const timeStr = `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
        const timestamp = `${targetDate}T${timeStr}:00`;

        // Venue2 to Venue1
        if (hour < venue2Schedule.closes || (hour === venue2Schedule.closes && minute === 0)) {
          // Only check time spent at venue2 if we're leaving at closing time
          if (hour === venue2Schedule.closes && minute === 0) {
            const hoursSpentAtVenue2 = hour - venue2Schedule.opens;
            if (hoursSpentAtVenue2 < venue2DwellHours) {
              console.log(`Skipping ${timeStr}: Can't leave at closing time, not enough time spent at ${venue2Data.venue_info.venue_name} (${hoursSpentAtVenue2.toFixed(1)} hours < ${venue2DwellHours} hours needed)`);
              continue;
            }
          }

          // Only check time at destination if it closes earlier than the starting venue
          if (venue1Schedule.closes <= venue2Schedule.closes) {
            // Estimate if there will be enough time at venue1
            const estimatedTravelTime = 30; // minutes
            const estimatedArrivalHour = hour + Math.floor(estimatedTravelTime / 60);
            const estimatedArrivalMinute = minute + (estimatedTravelTime % 60);
            const estimatedHoursUntilClose = venue1Schedule.closes - estimatedArrivalHour - (estimatedArrivalMinute / 60);

            if (estimatedHoursUntilClose < venue1DwellHours) {
              console.log(`Skipping ${timeStr}: Estimated only ${estimatedHoursUntilClose.toFixed(1)} hours available at ${venue1Data.venue_info.venue_name} (need ${venue1DwellHours} hours)`);
              continue;
            }
          }

          const routeKey = `${dayText}-${timeStr}-${venue2Data.venue_info.venue_name}-${venue1Data.venue_info.venue_name}`;
          if (!existingRouteMap.has(routeKey)) {
            console.log(`Fetching route: ${venue2Data.venue_info.venue_name} -> ${venue1Data.venue_info.venue_name} at ${timeStr}`);
            const route = await calculateRoute(
              venue2Data.venue_info.venue_lat,
              venue2Data.venue_info.venue_lon,
              venue1Data.venue_info.venue_lat,
              venue1Data.venue_info.venue_lon,
              timestamp
            );

            if (route.routes?.[0]) {
              const routeSummary = route.routes[0].summary;
              const travelTimeHours = routeSummary.travelTimeInSeconds / 3600;
              const arrivalHour = hour + Math.floor(travelTimeHours);
              const arrivalMinute = minute + Math.round((travelTimeHours % 1) * 60);
              
              // Only check actual time at destination if it closes earlier
              let shouldAddRoute = true;
              if (venue1Schedule.closes <= venue2Schedule.closes) {
                const hoursUntilClose = venue1Schedule.closes - arrivalHour - (arrivalMinute / 60);
                if (hoursUntilClose < venue1DwellHours) {
                  console.log(`Skipping route: Actual time available at ${venue1Data.venue_info.venue_name} (${hoursUntilClose.toFixed(1)} hours) is less than required`);
                  shouldAddRoute = false;
                }
              }
              
              if (shouldAddRoute) {
                newRoutes.push({
                  day: dayText,
                  time: timeStr,
                  from: venue2Data.venue_info.venue_name,
                  to: venue1Data.venue_info.venue_name,
                  distanceKm: Number((routeSummary.lengthInMeters / 1000).toFixed(2)),
                  travelTimeMinutes: Math.round(routeSummary.travelTimeInSeconds / 60),
                  trafficDelayMinutes: Math.round(routeSummary.trafficDelayInSeconds / 60)
                });
              }
            }
          }
        }
      }
    }
  }

  return newRoutes;
}

async function main() {
  // List of all venues
  const venues = [
    'cn_tower',
    'casa_loma',
    'royal_ontario_museum',
    'art_gallery_of_ontario',
    'distillery_historic_district',
    // 'hockey_hall_of_fame',
    // 'little_canada',
    // 'ripleys_aquarium_of_canada',
    // 'st_lawrence_market',
    // 'toronto_zoo',
  ];

  // Load all venue data
  const venueData = new Map<string, VenueData>();
  for (const venue of venues) {
    venueData.set(venue, await loadVenueData(venue));
  }

  // Load dwell times
  const dwellTimes = await loadDwellTimes();

  // Load existing routes
  const existingRoutes = await loadExistingRoutes();
  const existingRouteMap = new Map<string, RouteData>();
  existingRoutes.forEach(route => {
    const key = `${route.day}-${route.time}-${route.from}-${route.to}`;
    existingRouteMap.set(key, route);
  });

  const allRoutes: RouteData[] = [...existingRoutes];
  const newRoutes: RouteData[] = [];

  const daysToProcess = [
    { dayInt: 6, dayText: 'Sunday' },  // Was 0, now 6 for Sunday
    { dayInt: 0, dayText: 'Monday' },  // Was 1, now 0 for Monday
    { dayInt: 1, dayText: 'Tuesday' },  // Was 2, now 1 for Tuesday
    { dayInt: 2, dayText: 'Wednesday' },  // Was 3, now 2 for Wednesday
    { dayInt: 3, dayText: 'Thursday' },  // Was 4, now 3 for Thursday
    { dayInt: 4, dayText: 'Friday' },  // Was 5, now 4 for Friday
    { dayInt: 5, dayText: 'Saturday' },  // Was 6, now 5 for Saturday
  ];

  for (const { dayInt, dayText } of daysToProcess) {
    console.log(`\nProcessing routes for ${dayText}`);
    
    // Calculate routes between each pair of venues
    for (let i = 0; i < venues.length; i++) {
      for (let j = i + 1; j < venues.length; j++) {
        const venue1Data = venueData.get(venues[i])!;
        const venue2Data = venueData.get(venues[j])!;
        
        const venue1Schedule = getVenueSchedule(venue1Data)[dayInt];
        const venue2Schedule = getVenueSchedule(venue2Data)[dayInt];
        
        const venue1DwellHours = dwellTimes.get(venue1Data.venue_info.venue_name) || 3;
        const venue2DwellHours = dwellTimes.get(venue2Data.venue_info.venue_name) || 3;

        console.log(`Processing routes between ${venue1Data.venue_info.venue_name} and ${venue2Data.venue_info.venue_name}`);
        console.log(`${venue1Data.venue_info.venue_name} hours: ${venue1Schedule.opens}:00 - ${venue1Schedule.closes}:00`);
        console.log(`${venue2Data.venue_info.venue_name} hours: ${venue2Schedule.opens}:00 - ${venue2Schedule.closes}:00`);

        const pairRoutes = await calculateRoutesForVenuePair(
          venue1Data,
          venue2Data,
          venue1Schedule,
          venue2Schedule,
          venue1DwellHours,
          venue2DwellHours,
          dayText,
          existingRouteMap
        );

        newRoutes.push(...pairRoutes);
        allRoutes.push(...pairRoutes);
      }
    }
  }

  // Sort routes by day and time
  allRoutes.sort((a, b) => {
    const dayOrder = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const dayDiff = dayOrder.indexOf(a.day) - dayOrder.indexOf(b.day);
    if (dayDiff !== 0) return dayDiff;
    return a.time.localeCompare(b.time);
  });

  // Generate CSV content
  const headers = ['Day', 'Time', 'From', 'To', 'Distance (km)', 'Travel Time (min)', 'Traffic Delay (min)'];
  const csvContent = [
    headers.join(','),
    ...allRoutes.map(route => [
      route.day,
      route.time,
      route.from,
      route.to,
      route.distanceKm,
      route.travelTimeMinutes,
      route.trafficDelayMinutes
    ].join(','))
  ].join('\n');

  // Write to CSV file
  const csvPath = join(process.cwd(), 'data', 'timed_routes.csv');
  await writeFile(csvPath, csvContent);
  console.log(`\nRoute data has been saved to ${csvPath}`);
  console.log(`Added ${newRoutes.length} new routes`);
}

main().catch(console.error); 
