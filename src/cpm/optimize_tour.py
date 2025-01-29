"""Script to optimize a tour using the TourOptimizer model.

This script demonstrates how to use the TourOptimizer model with real data to
generate an optimized tour itinerary for Toronto attractions.
"""

from pathlib import Path
from typing import List
from .model import TourOptimizer
from .data_loader import DataLoader


def generate_time_slots() -> List[str]:
    """Generate time slots from 9:00 AM to 9:30 PM in 30-min intervals."""
    slots = []
    for hour in range(9, 22):  # 9:00 AM to 9:30 PM
        slots.append(f"{hour:02d}:00")
        slots.append(f"{hour:02d}:30")
    return slots


def main():
    """Main function to run the tour optimization."""
    # Set up paths
    data_dir = Path(__file__).parent.parent.parent / "data"
    
    # Initialize data loader
    data_loader = DataLoader(data_dir)
    
    # Generate time slots
    time_slots = generate_time_slots()
    
    # Load all required data
    (
        venue_data,
        dwell_times,
        travel_times,
        crowd_levels,
        venue_open_slots
    ) = data_loader.load_all(time_slots)
    
    # Get list of venues
    venues = list(dwell_times.keys())
    
    # Create optimizer for a Tuesday tour (ROM is closed on Mondays)
    optimizer = TourOptimizer(
        venues=venues,
        dwell_times=dwell_times,
        time_slots=time_slots,
        travel_times=travel_times,
        crowd_levels=crowd_levels,
        venue_open_slots=venue_open_slots,
        tour_start_time="09:00",
        tour_end_time="21:00",
        day="Tuesday"  # Type hint will ensure this is a valid DayOfWeek
    )
    
    # Solve the optimization problem
    solution = optimizer.solve()
    
    if solution:
        print("\nOptimized Tour Schedule:")
        print("=" * 50)
        
        # Print schedule
        for visit in solution["schedule"]:
            print(f"\n{visit['venue']}:")
            print(f"  Start time: {visit['start_time']}")
            print(f"  End time: {visit['end_time']}")
            print(f"  Duration: {visit['dwell_time_hours']:.1f} hours")
            print(f"  Crowd level: {visit['crowd_level_avg']:.1f}")
            if visit['travel_time_to_next'] is not None:
                travel_time = visit['travel_time_to_next']
                print(
                    "  Travel to next venue: "
                    f"{travel_time} min"
                )
        
        # Print metrics
        print("\nTour Metrics:")
        print("=" * 50)
        metrics = solution["metrics"]
        print(f"Total venues visited: {metrics['total_venues']}")
        print(
            f"Total travel time: "
            f"{metrics['total_travel_time_minutes']} minutes"
        )
        print(
            f"Average travel time: "
            f"{metrics['average_travel_time']:.1f} minutes"
        )
        print(
            f"Average crowd level: {metrics['average_crowd_level']:.1f}"
        )
    else:
        print("No valid solution found!")


if __name__ == "__main__":
    main() 