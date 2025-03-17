# Venue API Documentation

## Overview

The Venue API provides detailed information about venues, including their basic information, operating hours, and crowd patterns throughout the week. The response is structured in two main sections: venue information and analysis data.

## Response Structure

### Top Level Fields

| Field | Type | Description |
|-------|------|-------------|
| status | string | API response status (e.g., "OK") |
| venue_info | object | Contains basic venue information |
| analysis | array | Weekly analysis data, with each element representing a day |

### Venue Information Fields

The `venue_info` object contains the following fields:

| Field | Type | Description |
|-------|------|-------------|
| venue_id | string | Unique identifier for the venue |
| venue_name | string | Name of the venue |
| venue_address | string | Complete address as a single string |
| venue_address_list | array | Address broken down into components |
| venue_timezone | string | Timezone of the venue location |
| venue_dwell_time_min | integer | Minimum time visitors typically spend (minutes) |
| venue_dwell_time_max | integer | Maximum time visitors typically spend (minutes) |
| venue_dwell_time_avg | integer | Average time visitors spend (minutes) |
| venue_type | string | Primary category of the venue |
| venue_types | array | All applicable venue categories |
| venue_lat | number | Venue latitude |
| venue_lon | number | Venue longitude |

### Analysis Fields

Each day in the `analysis` array contains:

#### Day Information

The `day_info` object includes:

| Field | Type | Description |
|-------|------|-------------|
| day_int | integer | Day of week (0-6, starting from Monday) |
| day_text | string | Name of the day |
| day_rank_mean | integer | How busy the day is compared to other days (1 = busiest) |
| day_rank_max | integer | Peak busyness rank compared to other days |
| day_mean | integer | Average crowd level (0-100) |
| day_max | integer | Maximum crowd level (0-100) |
| venue_open_close_v2 | object | Operating hours in 12h and 24h formats |

#### Operating Hours (venue_open_close_v2)

| Field | Type | Description |
|-------|------|-------------|
| 24h | array | Contains objects with `opens` and `closes` times in 24-hour format |
| 12h | array | Contains time ranges in 12-hour format |

#### Crowd Analysis

| Field | Type | Description |
|-------|------|-------------|
| busy_hours | array | Hours considered busy (high traffic) |
| quiet_hours | array | Hours with notably low traffic |
| peak_hours | array | Detailed information about peak traffic periods |
| surge_hours | object | When most people arrive and leave |

#### Peak Hours Details

Each element in `peak_hours` contains:

| Field | Type | Description |
|-------|------|-------------|
| peak_start | integer | Hour when peak period begins |
| peak_max | integer | Hour with maximum traffic |
| peak_end | integer | Hour when peak period ends |
| peak_intensity | integer | Intensity level of the peak (1-5) |
| peak_delta_mean_week | integer | Difference from weekly average |

#### Hourly Analysis

The `hour_analysis` array contains 24 entries (one per hour) with:

| Field | Type | Description |
|-------|------|-------------|
| hour | integer | Hour of the day (0-23) |
| intensity_txt | string | Descriptive crowd level ("Low", "Average", etc.) |
| intensity_nr | integer | Numerical intensity (-2 to 2, 999 for closed) |

#### Raw Data

| Field | Type | Description |
|-------|------|-------------|
| day_raw | array | 24 values (0-100) representing hourly crowd levels |

## Notes

- Times are typically in 24-hour format unless specified otherwise
- Crowd levels are normalized on a 0-100 scale
- The API uses 999 as a special value to indicate closed hours
- Intensity levels range from -2 (very low) to 2 (very busy), with 0 being average
