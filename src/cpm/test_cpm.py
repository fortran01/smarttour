from typing import List, Dict, Tuple
from pathlib import Path
import pytest
from .model import TourOptimizer, DayOfWeek
from .data_loader import DataLoader


class TestTourOptimizer:
    @pytest.fixture
    def data_dir(self) -> Path:
        """Get the data directory path."""
        return Path(__file__).parent.parent.parent / "data"
    
    @pytest.fixture
    def data_loader(self, data_dir: Path) -> DataLoader:
        """Create a data loader instance."""
        return DataLoader(data_dir)
    
    @pytest.fixture
    def venue_data(self, data_loader: DataLoader) -> Dict:
        """Load venue data for testing."""
        return data_loader.load_venue_data()
    
    @pytest.fixture
    def dwell_times(self, data_loader: DataLoader) -> Dict[str, float]:
        """Load venue dwell times."""
        return data_loader.load_dwell_times()
    
    @pytest.fixture
    def time_slots(self) -> List[str]:
        """Generate time slots for testing (30 min intervals)."""
        slots = []
        for hour in range(9, 22):  # 9:00 AM to 9:30 PM
            slots.append(f"{hour:02d}:00")
            slots.append(f"{hour:02d}:30")
        return slots
    
    @pytest.fixture
    def travel_times(
        self,
        data_loader: DataLoader,
        time_slots: List[str]
    ) -> Dict[Tuple[str, str, str, DayOfWeek], int]:
        """Load travel times between venues."""
        return data_loader.load_travel_times(time_slots)
    
    @pytest.fixture
    def crowd_levels(
        self,
        data_loader: DataLoader,
        venue_data: Dict
    ) -> Dict[Tuple[str, str, DayOfWeek], int]:
        """Extract crowd levels from venue data."""
        return data_loader.extract_crowd_levels(venue_data)
    
    @pytest.fixture
    def venue_open_slots(
        self,
        data_loader: DataLoader,
        venue_data: Dict,
        time_slots: List[str]
    ) -> Dict[Tuple[str, DayOfWeek], List[int]]:
        """Extract venue operating hours."""
        return data_loader.extract_operating_hours(venue_data, time_slots)
    
    def test_basic_initialization(
        self,
        venue_data: Dict,
        dwell_times: Dict[str, float],
        time_slots: List[str],
        travel_times: Dict[Tuple[str, str, str, DayOfWeek], int],
        crowd_levels: Dict[Tuple[str, str, DayOfWeek], int],
        venue_open_slots: Dict[Tuple[str, DayOfWeek], List[int]]
    ):
        """Test basic initialization of TourOptimizer."""
        # Use a subset of venues for initial testing
        test_venues = list(dwell_times.keys())[:3]  # Start with 3 venues
        test_day: DayOfWeek = "Monday"  # Type annotation to ensure literal type
        
        optimizer = TourOptimizer(
            venues=test_venues,
            dwell_times={v: dwell_times[v] for v in test_venues},
            time_slots=time_slots,
            travel_times=travel_times,
            crowd_levels=crowd_levels,
            venue_open_slots=venue_open_slots,
            day=test_day
        )
        
        assert optimizer.venues == test_venues
        assert optimizer.n_venues == len(test_venues)
        assert optimizer.time_slots == time_slots
        assert optimizer.n_slots == len(time_slots)
        assert optimizer.day == test_day
    
    def test_solve_basic_tour(
        self,
        venue_data: Dict,
        dwell_times: Dict[str, float],
        time_slots: List[str],
        travel_times: Dict[Tuple[str, str, str, DayOfWeek], int],
        crowd_levels: Dict[Tuple[str, str, DayOfWeek], int],
        venue_open_slots: Dict[Tuple[str, DayOfWeek], List[int]]
    ):
        """Test solving a basic tour with 3 venues."""
        # Use 3 specific venues that we know should work together
        test_venues = ["CN Tower", "Casa Loma", "Royal Ontario Museum"]
        test_day: DayOfWeek = "Tuesday"  # Changed from Monday to Tuesday since ROM is closed on Mondays
        
        optimizer = TourOptimizer(
            venues=test_venues,
            dwell_times={v: dwell_times[v] for v in test_venues},
            time_slots=time_slots,
            travel_times=travel_times,
            crowd_levels=crowd_levels,
            venue_open_slots=venue_open_slots,
            tour_start_time="09:00",
            tour_end_time="21:00",
            day=test_day
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
                current_end,
                test_day
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
        travel_times: Dict[Tuple[str, str, str, DayOfWeek], int],
        crowd_levels: Dict[Tuple[str, str, DayOfWeek], int],
        venue_open_slots: Dict[Tuple[str, DayOfWeek], List[int]]
    ):
        """Test that solutions respect venue operating hours."""
        # Use CN Tower which has specific operating hours
        test_venues = ["CN Tower"]
        test_day: DayOfWeek = "Monday"
        
        # Get expected operating hours from venue data
        cn_tower_data = venue_data["CN Tower"]
        monday_data = next(
            day for day in cn_tower_data["analysis"] 
            if day["day_info"]["day_text"] == "Monday"
        )
        expected_open = monday_data["day_info"]["venue_open_close_v2"]["24h"][0]
        
        optimizer = TourOptimizer(
            venues=test_venues,
            dwell_times={v: dwell_times[v] for v in test_venues},
            time_slots=time_slots,
            travel_times=travel_times,
            crowd_levels=crowd_levels,
            venue_open_slots=venue_open_slots,
            tour_start_time="09:00",
            tour_end_time="21:00",
            day=test_day
        )
        
        solution = optimizer.solve()
        assert solution is not None, "Should find a valid solution"
        
        # Check that visit starts after opening time
        start_time = solution["schedule"][0]["start_time"]
        start_hour = int(start_time.split(":")[0])
        assert start_hour >= expected_open["opens"], (
            f"Visit starts at {start_time} but venue opens at "
            f"{expected_open['opens']}:00"
        )
        
        # Check that visit ends before closing time
        end_time = solution["schedule"][0]["end_time"]
        end_hour = int(end_time.split(":")[0])
        assert end_hour <= expected_open["closes"], (
            f"Visit ends at {end_time} but venue closes at "
            f"{expected_open['closes']}:00"
        )
    
    def test_travel_time_constraints(
        self,
        venue_data: Dict,
        dwell_times: Dict[str, float],
        time_slots: List[str],
        travel_times: Dict[Tuple[str, str, str, DayOfWeek], int],
        crowd_levels: Dict[Tuple[str, str, DayOfWeek], int],
        venue_open_slots: Dict[Tuple[str, DayOfWeek], List[int]]
    ):
        """Test that solutions respect travel times between venues."""
        # TODO: Implement this test after fixing the model
        pass 
    
    def test_different_days_operating_hours(
        self,
        venue_data: Dict,
        dwell_times: Dict[str, float],
        time_slots: List[str],
        travel_times: Dict[
            Tuple[str, str, str, DayOfWeek],
            int
        ],
        crowd_levels: Dict[
            Tuple[str, str, DayOfWeek],
            int
        ],
        venue_open_slots: Dict[
            Tuple[str, DayOfWeek],
            List[int]
        ]
    ):
        """Test that the model respects operating hours for different days."""
        test_venues = ["CN Tower"]
        # Test weekday vs weekend
        test_days: List[DayOfWeek] = ["Monday", "Saturday"]
        solutions: Dict[DayOfWeek, Dict] = {}
        
        # Get solutions for each day
        for day in test_days:
            optimizer = TourOptimizer(
                venues=test_venues,
                dwell_times={v: dwell_times[v] for v in test_venues},
                time_slots=time_slots,
                travel_times=travel_times,
                crowd_levels=crowd_levels,
                venue_open_slots=venue_open_slots,
                tour_start_time="09:00",
                tour_end_time="21:00",
                day=day
            )
            solution = optimizer.solve()
            assert solution is not None, f"Should find solution for {day}"
            solutions[day] = solution
        
        # Get expected operating hours for each day
        cn_tower_data = venue_data["CN Tower"]
        operating_hours = {}
        for day in test_days:
            day_data = next(
                d for d in cn_tower_data["analysis"]
                if d["day_info"]["day_text"] == day
            )
            hours = day_data["day_info"]["venue_open_close_v2"]["24h"][0]
            operating_hours[day] = hours
        
        # Check that visits respect day-specific operating hours
        for day in test_days:
            solution = solutions[day]
            schedule = solution["schedule"][0]  # Only one venue
            
            # Check start time
            start_time = schedule["start_time"]
            start_hour = int(start_time.split(":")[0])
            opens = operating_hours[day]["opens"]
            assert start_hour >= opens, (
                f"On {day}, visit starts at {start_time} but opens at "
                f"{opens}:00"
            )
            
            # Check end time
            end_time = schedule["end_time"]
            end_hour = int(end_time.split(":")[0])
            closes = operating_hours[day]["closes"]
            assert end_hour <= closes, (
                f"On {day}, visit ends at {end_time} but closes at "
                f"{closes}:00"
            )
    
    def test_different_days_crowd_levels(
        self,
        venue_data: Dict,
        dwell_times: Dict[str, float],
        time_slots: List[str],
        travel_times: Dict[
            Tuple[str, str, str, DayOfWeek],
            int
        ],
        crowd_levels: Dict[
            Tuple[str, str, DayOfWeek],
            int
        ],
        venue_open_slots: Dict[
            Tuple[str, DayOfWeek],
            List[int]
        ]
    ):
        """Test that the model handles crowd levels for different days."""
        test_venues = ["CN Tower"]
        # Test weekday vs weekend
        test_days: List[DayOfWeek] = ["Monday", "Saturday"]
        solutions: Dict[DayOfWeek, Dict] = {}
        
        # Get solutions for each day
        for day in test_days:
            optimizer = TourOptimizer(
                venues=test_venues,
                dwell_times={v: dwell_times[v] for v in test_venues},
                time_slots=time_slots,
                travel_times=travel_times,
                crowd_levels=crowd_levels,
                venue_open_slots=venue_open_slots,
                tour_start_time="09:00",
                tour_end_time="21:00",
                day=day
            )
            solution = optimizer.solve()
            assert solution is not None, f"Should find solution for {day}"
            solutions[day] = solution
        
        # Compare crowd levels between days
        crowd_metrics = {
            day: solution["schedule"][0]["crowd_level_avg"]
            for day, solution in solutions.items()
        }
        
        # Log crowd levels for analysis
        for day, crowd_level in crowd_metrics.items():
            print(f"{day} crowd level: {crowd_level}")
        
        # Note: We can't make absolute assertions about crowd levels
        # as the optimal solution depends on multiple factors
        # Instead, we verify that crowd levels are considered
        for day in test_days:
            schedule = solutions[day]["schedule"][0]
            assert "crowd_level_avg" in schedule
            assert isinstance(schedule["crowd_level_avg"], (int, float))
    
    def test_different_days_travel_times(
        self,
        venue_data: Dict,
        dwell_times: Dict[str, float],
        time_slots: List[str],
        travel_times: Dict[
            Tuple[str, str, str, DayOfWeek],
            int
        ],
        crowd_levels: Dict[
            Tuple[str, str, DayOfWeek],
            int
        ],
        venue_open_slots: Dict[
            Tuple[str, DayOfWeek],
            List[int]
        ]
    ):
        """Test that the model handles travel times for different days."""
        # Use two venues to test travel times between them
        test_venues = ["CN Tower", "Casa Loma"]
        # Test weekday vs weekend
        test_days: List[DayOfWeek] = ["Monday", "Saturday"]
        solutions: Dict[DayOfWeek, Dict] = {}
        
        # Get solutions for each day
        for day in test_days:
            optimizer = TourOptimizer(
                venues=test_venues,
                dwell_times={v: dwell_times[v] for v in test_venues},
                time_slots=time_slots,
                travel_times=travel_times,
                crowd_levels=crowd_levels,
                venue_open_slots=venue_open_slots,
                tour_start_time="09:00",
                tour_end_time="21:00",
                day=day
            )
            solution = optimizer.solve()
            assert solution is not None, f"Should find solution for {day}"
            solutions[day] = solution
        
        # Check travel times between venues for each day
        for day in test_days:
            solution = solutions[day]
            schedule = solution["schedule"]
            
            # Verify we have both venues in the solution
            assert len(schedule) == 2, f"Should visit both venues on {day}"
            
            # Check that travel time is respected
            first_visit = schedule[0]
            second_visit = schedule[1]
            
            # Get actual gap between visits
            actual_gap = (
                self._time_to_minutes(second_visit["start_time"]) -
                self._time_to_minutes(first_visit["end_time"])
            )
            
            # Get expected travel time
            travel_key = (
                first_visit["venue"],
                second_visit["venue"],
                first_visit["end_time"],
                day
            )
            expected_travel = travel_times[travel_key]
            
            # Format error message
            error_msg = (
                f"On {day}, gap between venues ({actual_gap} min) is less "
                f"than required travel time ({expected_travel} min)"
            )
            assert actual_gap >= expected_travel, error_msg 