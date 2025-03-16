"""Script to optimize a tour using the TourOptimizer model.

This script demonstrates how to use the TourOptimizer model with real data to
generate an optimized tour itinerary for Toronto attractions.
"""

import argparse
from pathlib import Path
from typing import List
from .model import TourOptimizer
from .data_loader import DataLoader


def generate_time_slots() -> List[str]:
    """Generate time slots from 9:00 AM to 10:30 PM in 30-min intervals."""
    slots = []
    for hour in range(9, 23):  # 9:00 AM to 10:30 PM
        slots.append(f"{hour:02d}:00")
        slots.append(f"{hour:02d}:30")
    return slots


def main():
    """Main function to run the tour optimization."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Optimize a tour itinerary using constraint programming"
    )
    parser.add_argument(
        "--cores", 
        type=int, 
        default=4,
        help="Number of CPU cores to use for parallel solving (default: 4)"
    )
    parser.add_argument(
        "--time-limit", 
        type=int, 
        default=300,
        help="Time limit in seconds for the solver (default: 300)"
    )
    parser.add_argument(
        "--day", 
        type=str, 
        # default="Monday",
        default="Tuesday",
        choices=[
            "Monday", "Tuesday", "Wednesday", "Thursday", 
            "Friday", "Saturday", "Sunday"
        ],
        help="Day of the week for the tour (default: Monday)"
    )
    args = parser.parse_args()
    
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
    
    # Create optimizer for the specified day
    optimizer = TourOptimizer(
        venues=venues,
        dwell_times=dwell_times,
        time_slots=time_slots,
        travel_times=travel_times,
        crowd_levels=crowd_levels,
        venue_open_slots=venue_open_slots,
        tour_start_time="09:00",
        tour_end_time="22:00",
        day=args.day  # Use the day from command line arguments
    )
    
    # Set custom objective weights
    optimizer.set_objective_weights(
        travel_weight=0.1,
        crowd_weight=0.1,
        venues_weight=-20
    )
    
    print(f"Optimizing tour for {args.day} using {args.cores} CPU cores...")
    print(f"Solver time limit: {args.time_limit} seconds")
    
    # Solve the optimization problem with multi-threading
    solution = optimizer.solve(
        num_cores=args.cores,
        time_limit=args.time_limit
    )
    
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