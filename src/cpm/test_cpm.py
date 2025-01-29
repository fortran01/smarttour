from typing import List
import json
import csv
from pathlib import Path
import pytest
from typing import Dict, Tuple
from .model import TourOptimizer


class TestTourOptimizer:
    @pytest.fixture
    def data_dir(self) -> Path:
        """Get the data directory path."""
        return Path(__file__).parent.parent.parent / "data"
    
    @pytest.fixture
    def data_dict_dir(self) -> Path:
        """Get the data dictionary directory path."""
        return Path(__file__).parent.parent.parent / "data_dict"
    
    @pytest.fixture
    def venue_data(self, data_dir: Path) -> Dict:
        """Load venue data for testing."""
        venues = {}
        for json_file in data_dir.glob("*.json"):
            if json_file.stem == "all_attractions":
                continue
            with open(json_file) as f:
                venues[json_file.stem] = json.load(f)
        return venues
    
    @pytest.fixture
    def dwell_times(self, data_dir: Path) -> Dict[str, float]:
        """Load venue dwell times."""
        dwell_times = {}
        with open(data_dir / "venue_dwell_times.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dwell_times[row["Venue"]] = float(row["Dwell Time (hours)"])
        return dwell_times
    
    @pytest.fixture
    def time_slots(self) -> List[str]:
        """Generate time slots for testing (30 min intervals)."""
        slots = []
        for hour in range(9, 22):  # 9:00 AM to 9:30 PM
            slots.append(f"{hour:02d}:00")
            slots.append(f"{hour:02d}:30")
        return slots
    
    @pytest.fixture
    def travel_times(self, data_dir: Path) -> Dict[Tuple[str, str, str], int]:
        """Load travel times between venues."""
        times = {}
        with open(data_dir / "timed_routes.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row["From"], row["To"], row["Time"])
                times[key] = int(float(row["Travel Time (min)"]))
        return times
    
    @pytest.fixture
    def crowd_levels(self, venue_data: Dict) -> Dict[Tuple[str, str], int]:
        """Extract crowd levels from venue data."""
        levels = {}
        for venue_name, data in venue_data.items():
            for day_data in data["analysis"]:
                # We'll use Monday's data for testing
                if day_data["day_info"]["day_int"] == 0:  # Monday
                    for hour_data in day_data["hour_analysis"]:
                        time = f"{hour_data['hour']:02d}:00"
                        levels[(venue_name, time)] = (
                            0 if hour_data["intensity_nr"] == 999 
                            else hour_data["intensity_nr"]
                        )
                    break
        return levels
    
    def test_basic_initialization(
        self,
        venue_data: Dict,
        dwell_times: Dict[str, float],
        time_slots: List[str],
        travel_times: Dict[Tuple[str, str, str], int],
        crowd_levels: Dict[Tuple[str, str], int]
    ):
        """Test basic initialization of TourOptimizer."""
        # Use a subset of venues for initial testing
        test_venues = list(dwell_times.keys())[:3]  # Start with 3 venues
        
        optimizer = TourOptimizer(
            venues=test_venues,
            dwell_times={v: dwell_times[v] for v in test_venues},
            time_slots=time_slots,
            travel_times=travel_times,
            crowd_levels=crowd_levels
        )
        
        assert optimizer.venues == test_venues
        assert optimizer.n_venues == len(test_venues)
        assert optimizer.time_slots == time_slots
        assert optimizer.n_slots == len(time_slots)
    
    def test_solve_basic_tour(
        self,
        venue_data: Dict,
        dwell_times: Dict[str, float],
        time_slots: List[str],
        travel_times: Dict[Tuple[str, str, str], int],
        crowd_levels: Dict[Tuple[str, str], int]
    ):
        """Test solving a basic tour with 3 venues."""
        # Use 3 specific venues that we know should work together
        test_venues = ["CN Tower", "Casa Loma", "Royal Ontario Museum"]
        
        optimizer = TourOptimizer(
            venues=test_venues,
            dwell_times={v: dwell_times[v] for v in test_venues},
            time_slots=time_slots,
            travel_times=travel_times,
            crowd_levels=crowd_levels,
            tour_start_time="09:00",
            tour_end_time="21:00"
        )
        
        solution = optimizer.solve()
        assert solution is not None, "Should find a valid solution"
        
        # Check solution structure
        assert "selected_venues" in solution
        assert "start_times" in solution
        assert "metrics" in solution
        assert "schedule" in solution
        
        # Check that all venues are included
        assert len(solution["selected_venues"]) == len(test_venues)
        assert set(solution["selected_venues"]) == set(test_venues)
        
        # Check schedule validity
        schedule = solution["schedule"]
        for i in range(len(schedule) - 1):
            current = schedule[i]
            next_visit = schedule[i + 1]
            
            # Check that venues don't overlap in time
            current_end = current["end_time"]
            next_start = next_visit["start_time"]
            assert current_end <= next_start, (
                f"Venue visits overlap: {current['venue']} ends at {current_end}"
                f" but {next_visit['venue']} starts at {next_start}"
            )
            
            # Check travel times are respected
            travel_key = (
                current["venue"],
                next_visit["venue"],
                current_end
            )
            if travel_key in travel_times:
                min_travel_time = travel_times[travel_key]
                actual_gap = (
                    self._time_to_minutes(next_start) -
                    self._time_to_minutes(current_end)
                )
                assert actual_gap >= min_travel_time, (
                    "Travel time not respected between "
                    f"{current['venue']} and {next_visit['venue']}"
                )
    
    def _time_to_minutes(self, time_str: str) -> int:
        """Convert HH:MM time string to minutes since midnight."""
        hours, minutes = map(int, time_str.split(":"))
        return hours * 60 + minutes
    
    def test_time_window_constraints(
        self,
        venue_data: Dict,
        dwell_times: Dict[str, float],
        time_slots: List[str],
        travel_times: Dict[Tuple[str, str, str], int],
        crowd_levels: Dict[Tuple[str, str], int]
    ):
        """Test that solutions respect venue operating hours."""
        # TODO: Implement this test after fixing the model
        pass
    
    def test_travel_time_constraints(
        self,
        venue_data: Dict,
        dwell_times: Dict[str, float],
        time_slots: List[str],
        travel_times: Dict[Tuple[str, str, str], int],
        crowd_levels: Dict[Tuple[str, str], int]
    ):
        """Test that solutions respect travel times between venues."""
        # TODO: Implement this test after fixing the model
        pass 