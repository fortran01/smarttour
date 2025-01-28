# Venue Dwell Times Data Dictionary

## Overview

The `venue_dwell_times.csv` file contains information about the estimated time visitors typically spend at various Toronto attractions, sourced mostly from Google Maps data. This data is used for tour planning and itinerary optimization.

## File Format

- File type: CSV (Comma-Separated Values)
- Encoding: UTF-8
- Header row: Yes
- Delimiter: Comma (,)

## Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Venue | string | The name of the tourist attraction or venue | "CN Tower" |
| Dwell Time (hours) | float | The estimated time in hours that visitors typically spend at the venue | 3.0 |

## Notes

- Dwell times are specified in decimal hours
- Values are based on average visitor behavior and recommended visit durations
- These times are used as default values for tour planning algorithms
- Times may vary based on individual preferences, season, or special events

## Example Record

```csv
CN Tower,3
```

## Usage

This data is primarily used for:
- Calculating total tour durations
- Optimizing multi-venue tour routes
- Providing estimated visit duration information to users
- Tour scheduling and time management 