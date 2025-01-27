# Route API Documentation

## Overview

The Route API provides detailed information about travel routes, including settings, route summaries, and detailed leg information with geographic points. The response is structured in three main sections: format version, report settings, and route data.

## Response Structure

### Top Level Fields

| Field | Type | Description |
|-------|------|-------------|
| formatVersion | string | API format version identifier |
| report | object | Contains effective settings for the route |
| routes | array | Contains the route information and details |

### Report Settings

The `report.effectiveSettings` array contains objects with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| key | string | Setting identifier |
| value | string | Setting value |

Key settings include:

| Setting Key | Description |
|-------------|-------------|
| avoid | Road types to avoid (e.g., "unpavedRoads") |
| computeBestOrder | Whether to optimize stop order |
| computeTravelTimeFor | Time calculation mode |
| departAt | Departure time in ISO format |
| locations | Start and end coordinates |
| routeType | Route optimization type (e.g., "fastest") |
| travelMode | Mode of transportation |
| traffic | Whether to include traffic data |

### Route Information

Each route in the `routes` array contains:

#### Route Summary

| Field | Type | Description |
|-------|------|-------------|
| lengthInMeters | integer | Total route distance in meters |
| travelTimeInSeconds | integer | Total travel time including traffic |
| trafficDelayInSeconds | integer | Additional time due to traffic |
| trafficLengthInMeters | integer | Distance affected by traffic |
| departureTime | string | Route start time (ISO format) |
| arrivalTime | string | Estimated arrival time (ISO format) |
| noTrafficTravelTimeInSeconds | integer | Travel time without traffic |
| historicTrafficTravelTimeInSeconds | integer | Travel time based on historical traffic |
| liveTrafficIncidentsTravelTimeInSeconds | integer | Travel time considering live incidents |

#### Route Legs

Each route contains a `legs` array with detailed segment information:

##### Leg Summary
Contains the same fields as the route summary but for the specific leg.

##### Points
The `points` array contains geographic coordinates:

| Field | Type | Description |
|-------|------|-------------|
| latitude | number | Point latitude |
| longitude | number | Point longitude |

## Vehicle Settings

The API includes various vehicle-specific settings:

| Setting | Description |
|---------|-------------|
| vehicleAxleWeight | Vehicle axle weight |
| vehicleCommercial | Commercial vehicle indicator |
| vehicleEngineType | Engine type (e.g., "combustion") |
| vehicleHeight | Vehicle height |
| vehicleLength | Vehicle length |
| vehicleMaxSpeed | Maximum speed limit |
| vehicleNumberOfAxles | Number of axles |
| vehicleWeight | Total vehicle weight |
| vehicleWidth | Vehicle width |

## Notes

- All times are provided in both local timezone and ISO format
- Distances are in meters
- Times are in seconds
- Geographic coordinates use WGS84 format
- Vehicle dimensions are in meters
- Vehicle weights are in appropriate weight units (not specified in sample)
- Traffic calculations include historical, real-time, and incident-based data