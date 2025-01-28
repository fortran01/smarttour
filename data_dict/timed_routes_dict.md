# Data Dictionary: timed_routes.csv

## Overview
This file contains pre-calculated route timing data between Toronto attractions, including traffic conditions and travel times for different days and time slots. The data is used by SmartTour to optimize tourist itineraries.

## Fields

### Day
- **Description**: Day of the week for the route timing
- **Data Type**: String
- **Possible Values**: Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday
- **Example**: "Sunday"

### Time
- **Description**: Time slot for departure in 24-hour format
- **Data Type**: String (HH:MM)
- **Range**: 10:00 to 17:00 in 30-minute intervals
- **Example**: "10:00"

### From
- **Description**: Starting venue/attraction for the route
- **Data Type**: String
- **Current Venues**: CN Tower, Casa Loma, Royal Ontario Museum
- **Example**: "CN Tower"

### To
- **Description**: Destination venue/attraction for the route
- **Data Type**: String
- **Current Venues**: CN Tower, Casa Loma, Royal Ontario Museum
- **Example**: "Casa Loma"

### Distance (km)
- **Description**: Travel distance between venues in kilometers
- **Data Type**: Decimal number (to 2 decimal places)
- **Range**: 2.75 to 6.03 km (based on current data)
- **Example**: 5.51

### Travel Time (min)
- **Description**: Estimated travel time in minutes, including current traffic conditions
- **Data Type**: Integer
- **Range**: 10 to 30 minutes (based on current data)
- **Example**: 21

### Traffic Delay (min)
- **Description**: Additional delay due to traffic conditions in minutes
- **Data Type**: Integer
- **Range**: 0+ minutes (currently all 0 in sample data)
- **Example**: 0

## Notes
1. Time slots are available every 30 minutes during typical tourist hours (10:00-17:00)
2. Routes are calculated bi-directionally between venues (A→B and B→A)
3. Travel times include real-time traffic conditions from TomTom's Routing API
4. Distance and travel time may vary between directions due to one-way streets and route optimization
5. Data is refreshed periodically to maintain accuracy of traffic patterns

## Related Files
- `venue_dwell_times.csv`: Contains minimum recommended visit durations for each venue
- `bettertime_dict.md`: Data dictionary for BetterTime.app integration
- `route_dict.md`: Data dictionary for route calculations 