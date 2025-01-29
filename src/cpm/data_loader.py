"""Data loading utilities for the CPM module.

This module provides functions to load and validate venue data, including:
- Operating hours by day
- Crowd levels by day and time
- Travel times between venues by day and time
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Tuple, cast
from .model import DayOfWeek, DAY_TO_INT


class DataLoader:
    """Loads and validates venue data for the tour optimizer."""
    
    def __init__(self, data_dir: Path):
        """Initialize the data loader.
        
        Args:
            data_dir: Path to directory containing data files
        """
        self.data_dir = data_dir
    
    def load_venue_data(self) -> Dict[str, Dict]:
        """Load venue data from JSON files.
        
        Returns:
            Dict mapping venue name to venue data
        
        Raises:
            FileNotFoundError: If venue data files not found
            JSONDecodeError: If venue data files are invalid JSON
        """
        venues = {}
        for json_file in self.data_dir.glob("*.json"):
            if json_file.stem == "all_attractions":
                continue
            # Convert filename to proper venue name (e.g., "cn_tower" -> "CN Tower")
            venue_name = json_file.stem.replace("_", " ").title()
            if venue_name == "Cn Tower":
                venue_name = "CN Tower"
            with open(json_file) as f:
                venues[venue_name] = json.load(f)
        return venues
    
    def load_dwell_times(self) -> Dict[str, float]:
        """Load venue dwell times from CSV.
        
        Returns:
            Dict mapping venue name to dwell time in hours
        
        Raises:
            FileNotFoundError: If dwell times file not found
            ValueError: If dwell times are invalid
        """
        dwell_times = {}
        dwell_times_file = self.data_dir / "venue_dwell_times.csv"
        with open(dwell_times_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                dwell_times[row["Venue"]] = float(row["Dwell Time (hours)"])
        return dwell_times
    
    def load_travel_times(
        self,
        time_slots: List[str]
    ) -> Dict[Tuple[str, str, str, DayOfWeek], int]:
        """Load travel times between venues.
        
        Args:
            time_slots: List of time slots in HH:MM format
        
        Returns:
            Dict mapping (from,to,time,day) to travel time in minutes
        
        Raises:
            FileNotFoundError: If travel times file not found
            ValueError: If travel times are invalid
        """
        times: Dict[Tuple[str, str, str, DayOfWeek], int] = {}
        travel_times_file = self.data_dir / "timed_routes.csv"
        
        # Helper function to find nearest time slot
        def find_nearest_time(target: str, available_times: List[str]) -> str:
            if target in available_times:
                return target
            # Convert all times to minutes since midnight
            target_mins = int(target.split(":")[0]) * 60 + \
                         int(target.split(":")[1])
            time_mins = [(t, int(t.split(":")[0]) * 60 + \
                         int(t.split(":")[1])) for t in available_times]
            # Find closest time by absolute difference
            closest = min(time_mins, key=lambda x: abs(x[1] - target_mins))
            return closest[0]
        
        # First pass: collect available times for each venue pair
        available_times: Dict[Tuple[str, str], List[str]] = {}
        with open(travel_times_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                venue_pair = (row["From"], row["To"])
                if venue_pair not in available_times:
                    available_times[venue_pair] = []
                available_times[venue_pair].append(row["Time"])
        
        # Second pass: load times and fill in missing slots
        with open(travel_times_file) as f:
            reader = csv.DictReader(f)
            base_times = {}  # Store base travel times
            for row in reader:
                venue_pair = (row["From"], row["To"])
                base_times[(venue_pair, row["Time"])] = \
                    int(float(row["Travel Time (min)"]))
        
        # Fill in all time slots for each venue pair
        for venue_pair, avail_times in available_times.items():
            for time_slot in time_slots:
                nearest = find_nearest_time(time_slot, avail_times)
                travel_time = base_times[(venue_pair, nearest)]
                # Add travel time for all days
                for day_name in DAY_TO_INT.keys():
                    day = cast(DayOfWeek, day_name)
                    times[(venue_pair[0], venue_pair[1], time_slot, day)] = \
                        travel_time
        
        return times
    
    def extract_crowd_levels(
        self,
        venue_data: Dict[str, Dict]
    ) -> Dict[Tuple[str, str, DayOfWeek], int]:
        """Extract crowd levels from venue data.
        
        Args:
            venue_data: Dict mapping venue name to venue data
        
        Returns:
            Dict mapping (venue, time_slot, day) to crowd level
        """
        levels: Dict[Tuple[str, str, DayOfWeek], int] = {}
        
        for venue_name, data in venue_data.items():
            for day_data in data["analysis"]:
                day_int = day_data["day_info"]["day_int"]
                day_name = list(DAY_TO_INT.keys())[day_int]
                day = cast(DayOfWeek, day_name)
                
                for hour_data in day_data["hour_analysis"]:
                    time = f"{hour_data['hour']:02d}:00"
                    levels[(venue_name, time, day)] = (
                        0 if hour_data["intensity_nr"] == 999 
                        else hour_data["intensity_nr"]
                    )
        return levels
    
    def extract_operating_hours(
        self,
        venue_data: Dict[str, Dict],
        time_slots: List[str]
    ) -> Dict[Tuple[str, DayOfWeek], List[int]]:
        """Extract venue operating hours.
        
        Args:
            venue_data: Dict mapping venue name to venue data
            time_slots: List of time slots in HH:MM format
        
        Returns:
            Dict mapping (venue, day) to list of valid time slot indices
        """
        slots: Dict[Tuple[str, DayOfWeek], List[int]] = {}
        
        # Helper function to convert HH to slot index
        def hour_to_slot_index(hour: int) -> int:
            return (hour - 9) * 2  # 9:00 is slot 0, each hour is 2 slots
        
        for venue_name, data in venue_data.items():
            for day_data in data["analysis"]:
                day_int = day_data["day_info"]["day_int"]
                day_name = list(DAY_TO_INT.keys())[day_int]
                day = cast(DayOfWeek, day_name)
                
                # Get operating hours for this day
                open_close = day_data["day_info"]["venue_open_close_v2"]["24h"]
                valid_slots: List[int] = []
                
                for period in open_close:
                    opens = period["opens"]  # Opening hour
                    closes = period["closes"]  # Closing hour
                    
                    # Convert hours to slot indices
                    start_slot = max(0, hour_to_slot_index(opens))
                    end_slot = min(
                        len(time_slots),
                        hour_to_slot_index(closes)
                    )
                    
                    # Add all valid slots for this period
                    valid_slots.extend(range(start_slot, end_slot))
                
                slots[(venue_name, day)] = sorted(list(set(valid_slots)))
        
        return slots
    
    def load_all(
        self,
        time_slots: List[str]
    ) -> Tuple[
        Dict[str, Dict],
        Dict[str, float],
        Dict[Tuple[str, str, str, DayOfWeek], int],
        Dict[Tuple[str, str, DayOfWeek], int],
        Dict[Tuple[str, DayOfWeek], List[int]]
    ]:
        """Load all required data for the tour optimizer.
        
        Args:
            time_slots: List of time slots in HH:MM format
        
        Returns:
            Tuple containing:
            - venue_data: Raw venue data
            - dwell_times: Venue dwell times
            - travel_times: Travel times between venues
            - crowd_levels: Crowd levels by venue, time and day
            - operating_hours: Valid time slots by venue and day
        """
        venue_data = self.load_venue_data()
        dwell_times = self.load_dwell_times()
        travel_times = self.load_travel_times(time_slots)
        crowd_levels = self.extract_crowd_levels(venue_data)
        operating_hours = self.extract_operating_hours(venue_data, time_slots)
        
        return (
            venue_data,
            dwell_times,
            travel_times,
            crowd_levels,
            operating_hours
        ) 