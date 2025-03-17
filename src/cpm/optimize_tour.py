"""Script to optimize a tour using the TourOptimizer model.

This script demonstrates how to use the TourOptimizer model with real data to
generate an optimized tour itinerary for Toronto attractions.
"""

import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
from .model import TourOptimizer
from .data_loader import DataLoader


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_time_slots() -> List[str]:
    """Generate time slots from 9:00 AM to 10:30 PM in 30-min intervals."""
    slots = []
    for hour in range(9, 23):
        slots.append(f"{hour:02d}:00")
        slots.append(f"{hour:02d}:30")
    return slots


def analyze_venue_constraints(
    venues: List[str],
    dwell_times: Dict[str, float],
    venue_open_slots: Dict[Any, List[int]],
    time_slots: List[str],
    day: str
) -> None:
    """Analyze and log venue constraints that might affect selection.
    
    Args:
        venues: List of venue names
        dwell_times: Dict mapping venue to dwell time in hours
        venue_open_slots: Dict mapping (venue, day) to list of valid slots
        time_slots: List of time slots in HH:MM format
        day: Day of the week for the tour
    """
    logger.info("Analyzing venue constraints that might affect selection:")
    
    # Check if any venues have no open slots for the selected day
    venues_without_slots = []
    for venue in venues:
        key = (venue, day)
        if key not in venue_open_slots or not venue_open_slots[key]:
            venues_without_slots.append(venue)
    
    if venues_without_slots:
        logger.warning(
            f"The following venues have no open slots on {day}: "
            f"{', '.join(venues_without_slots)}"
        )
    
    # Log dwell times for each venue
    logger.info("Venue dwell times:")
    for venue in venues:
        logger.info(f"  {venue}: {dwell_times[venue]:.1f} hours")
    
    # Log opening hours for each venue
    logger.info(f"Venue opening hours on {day}:")
    for venue in venues:
        key = (venue, day)
        if key in venue_open_slots and venue_open_slots[key]:
            open_slots = venue_open_slots[key]
            if open_slots:
                start_slot = min(open_slots)
                end_slot = max(open_slots)
                if start_slot < len(time_slots) and end_slot < len(time_slots):
                    start_time = time_slots[start_slot]
                    # Add dwell time to get the latest possible start time
                    latest_start_slot = end_slot - int(dwell_times[venue] * 2) + 1
                    latest_start_time = time_slots[max(0, min(latest_start_slot, len(time_slots)-1))]
                    logger.info(
                        f"  {venue}: Opens at {start_time}, "
                        f"Latest start time: {latest_start_time}"
                    )
                else:
                    logger.warning(f"  {venue}: Invalid slot indices")
            else:
                logger.warning(f"  {venue}: No open slots on {day}")
        else:
            logger.warning(f"  {venue}: No opening hours data for {day}")


def analyze_objective_weights(
    travel_weight: float,
    crowd_weight: float,
    venues_weight: float
) -> None:
    """Analyze and log the objective weights that might affect venue selection.
    
    Args:
        travel_weight: Weight for travel time minimization
        crowd_weight: Weight for crowd level minimization
        venues_weight: Weight for venue count maximization
    """
    logger.info("Analyzing objective weights:")
    logger.info(f"  Travel weight: {travel_weight}")
    logger.info(f"  Crowd weight: {crowd_weight}")
    logger.info(f"  Venues weight: {venues_weight}")
    
    if travel_weight == 0 and crowd_weight == 0:
        logger.warning(
            "Both travel and crowd weights are set to 0. "
            "This means the optimizer will only consider maximizing the number "
            "of venues without considering travel time or crowd levels."
        )
    
    if venues_weight == 0:
        logger.warning(
            "Venues weight is set to 0. "
            "This means the optimizer has no incentive to include venues in the tour."
        )
    elif venues_weight > 0:
        logger.warning(
            "Venues weight is positive. "
            "This means the optimizer will try to MINIMIZE the number of venues. "
            "For maximizing venues, this weight should be negative."
        )


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
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--debug-constraints", 
        action="store_true",
        help="Enable detailed constraint debugging"
    )
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(f"Starting tour optimization for {args.day}")
    
    # Set up paths
    data_dir = Path(__file__).parent.parent.parent / "data"
    logger.info(f"Using data directory: {data_dir}")
    
    # Initialize data loader
    data_loader = DataLoader(data_dir)
    
    # Generate time slots
    time_slots = generate_time_slots()
    logger.info(f"Generated {len(time_slots)} time slots from {time_slots[0]} to {time_slots[-1]}")
    
    # Load all required data
    logger.info("Loading venue data...")
    (
        venue_data,
        dwell_times,
        travel_times,
        crowd_levels,
        venue_open_slots
    ) = data_loader.load_all(time_slots)
    
    # Get list of venues
    venues = list(dwell_times.keys())
    logger.info(f"Loaded data for {len(venues)} venues: {', '.join(venues)}")
    
    # Analyze venue constraints
    analyze_venue_constraints(
        venues,
        dwell_times,
        venue_open_slots,
        time_slots,
        args.day
    )
    
    # Set custom objective weights to strongly favor multiple venues
    # Keep travel and crowd weights low to prioritize venue count
    # travel_weight = 0.05   # Reduced weight for travel time
    travel_weight = 0.4
    # crowd_weight = 0.05    # Reduced weight for crowds
    crowd_weight = 0.4
    # venues_weight = -5000  # Much stronger weight to maximize venues
    venues_weight = -1
    
    # Analyze objective weights
    analyze_objective_weights(
        travel_weight,
        crowd_weight,
        venues_weight
    )
    
    # Check for missing travel time data and add default values
    logger.info("Checking for missing travel time data...")
    for from_venue in venues:
        for to_venue in venues:
            if from_venue != to_venue:
                # Check a sample time slot
                sample_time = time_slots[0]
                travel_key = (from_venue, to_venue, sample_time, args.day)
                if travel_key not in travel_times:
                    # Add a default travel time (30 minutes)
                    logger.warning(
                        f"Missing travel time from {from_venue} to {to_venue}. "
                        f"Adding default value of 30 minutes."
                    )
                    for time_slot in time_slots:
                        travel_times[(from_venue, to_venue, time_slot, args.day)] = 30
    
    # Create optimizer for the specified day
    optimizer = TourOptimizer(
        venues=venues,
        dwell_times=dwell_times,
        time_slots=time_slots,
        travel_times=travel_times,
        crowd_levels=crowd_levels,
        venue_open_slots=venue_open_slots,
        tour_start_time="09:00",  # Keep early start
        tour_end_time="22:30",    # Extended to allow more venues
        day=args.day  # Use the day from command line arguments
    )
    
    # Set aggressive minimum venues target with optimized solver
    min_venues = 3 if args.day == "Monday" else 4
    optimizer.set_min_venues(min_venues)

    # Set custom objective weights with strong preference for multiple venues
    optimizer.set_objective_weights(
        travel_weight=travel_weight,
        crowd_weight=crowd_weight,
        venues_weight=venues_weight
    )
    
    # Debug: Log the constraint model details if requested
    if args.debug_constraints:
        logger.info("Constraint model details:")
        # The Model object doesn't have a 'variables' attribute we can access directly
        # logger.info(f"Number of variables: {len(optimizer.model.variables)}")
        # logger.info(f"Number of constraints: {len(optimizer.model.constraints)}")
        
        # Log time window constraints
        logger.info("Time window constraints:")
        for i, venue in enumerate(venues):
            key = (venue, args.day)
            if key in venue_open_slots:
                valid_slots = venue_open_slots[key]
                logger.info(f"  {venue}: {len(valid_slots)} valid slots")
                
                # Check if venue can fit within tour hours
                dwell_slots = optimizer.dwell_slots[venue]
                can_fit = False
                for slot in valid_slots:
                    if slot + dwell_slots <= optimizer.tour_end_slot:
                        can_fit = True
                        break
                logger.info(f"  {venue}: Can fit within tour hours: {can_fit}")
    
    logger.info(f"Optimizing tour for {args.day} using {args.cores} CPU cores...")
    logger.info(f"Solver time limit: {args.time_limit} seconds")
    
    # Try multiple iterations with increasing time limits to check for local optima
    solutions = []
    time_increments = [30, 60, 120, args.time_limit]
    
    for i, time_limit in enumerate(time_increments):
        if time_limit > args.time_limit:
            break
            
        logger.info(f"Solving attempt {i+1} with time limit: {time_limit} seconds")
        
        # Solve the optimization problem with multi-threading
        solution = optimizer.solve(
            num_cores=args.cores,
            time_limit=time_limit
        )
        
        if solution:
            selected_venues = solution.get("selected_venues", [])
            logger.info(f"Solution found with {len(selected_venues)} venues: {', '.join(selected_venues)}")
            solutions.append((time_limit, solution))
    
    # Check if solutions improved over time (indicating local optima issues)
    if len(solutions) > 1:
        logger.info("Analyzing solution progression:")
        for i, (time_limit, solution) in enumerate(solutions):
            venues_count = len(solution.get("selected_venues", []))
            logger.info(f"  Time limit {time_limit}s: {venues_count} venues")
            
        # Check if later solutions have more venues
        improved = False
        for i in range(1, len(solutions)):
            prev_count = len(solutions[i-1][1].get("selected_venues", []))
            curr_count = len(solutions[i][1].get("selected_venues", []))
            if curr_count > prev_count:
                improved = True
                logger.info(f"Solution improved from {prev_count} to {curr_count} venues with more time")
                
        if improved:
            logger.warning("Solver appears to be getting stuck in local optima - solutions improved with more time")
        else:
            logger.info("No improvement in solutions with more time - likely not a local optima issue")
    
    # Use the final solution
    solution = solutions[-1][1] if solutions else None
    
    if solution:
        logger.info("Final solution found!")
        selected_venues = solution.get("selected_venues", [])
        logger.info(f"Selected venues: {', '.join(selected_venues)}")
        
        # Log why only one venue might have been selected
        if len(selected_venues) == 1:
            logger.warning(
                f"Only one venue ({selected_venues[0]}) was selected. "
                "This could be due to:"
            )
            logger.warning(
                "1. Tight time constraints: The tour start/end times might not "
                "allow visiting multiple venues with their required dwell times."
            )
            logger.warning(
                "2. Venue opening hours: Other venues might not be open during "
                f"the specified day ({args.day}) or have limited hours."
            )
            logger.warning(
                "3. Objective weights: The current weights "
                f"(travel={travel_weight}, crowd={crowd_weight}, "
                f"venues={venues_weight}) might not provide enough incentive "
                "to visit multiple venues."
            )
            logger.warning(
                "4. Solver time limit: The solver might not have had enough time "
                "to find a solution with more venues."
            )
            
            # Additional debugging for single venue case
            logger.warning("Detailed constraint analysis for single venue case:")
            
            # Check if any venues could theoretically be added
            selected_venue = selected_venues[0]
            selected_idx = venues.index(selected_venue)
            selected_start_slot = time_slots.index(solution["start_times"][selected_venue])
            selected_end_slot = selected_start_slot + optimizer.dwell_slots[selected_venue]
            
            logger.warning(f"Selected venue {selected_venue} occupies slots {selected_start_slot}-{selected_end_slot}")
            
            # Check each other venue to see if it could fit before or after
            for i, venue in enumerate(venues):
                if venue == selected_venue:
                    continue
                    
                dwell = optimizer.dwell_slots[venue]
                key = (venue, args.day)
                
                if key in venue_open_slots:
                    valid_slots = venue_open_slots[key]
                    
                    # Check if venue could fit before selected venue
                    could_fit_before = False
                    for slot in valid_slots:
                        if slot + dwell <= selected_start_slot:
                            could_fit_before = True
                            break
                            
                    # Check if venue could fit after selected venue
                    could_fit_after = False
                    for slot in valid_slots:
                        if slot >= selected_end_slot and slot + dwell <= optimizer.tour_end_slot:
                            could_fit_after = True
                            break
                            
                    logger.warning(f"  {venue}: Could fit before: {could_fit_before}, Could fit after: {could_fit_after}")
                    
                    # If venue could fit but wasn't selected, investigate why
                    if could_fit_before or could_fit_after:
                        # Check travel times
                        if could_fit_before:
                            end_time = time_slots[min(valid_slots[0] + dwell, len(time_slots)-1)]
                            travel_key = (venue, selected_venue, end_time, args.day)
                            travel_time = travel_times.get(travel_key, "unknown")
                            logger.warning(f"    Travel time from {venue} to {selected_venue}: {travel_time}")
                            
                        if could_fit_after:
                            start_time = time_slots[selected_end_slot]
                            travel_key = (selected_venue, venue, start_time, args.day)
                            travel_time = travel_times.get(travel_key, "unknown")
                            logger.warning(f"    Travel time from {selected_venue} to {venue}: {travel_time}")
        
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
        
        # Print explanation for single venue selection
        if len(selected_venues) == 1:
            print("\nWhy only one venue was selected:")
            print("=" * 50)
            print(
                "The optimizer selected only one venue due to a combination of factors:\n"
                "1. Time constraints: The tour's time window might be too narrow for multiple venues\n"
                "2. Venue opening hours: Other venues might have limited hours on this day\n"
                "3. Objective weights: Current weights might not incentivize multiple venues enough\n"
                "4. Solver limitations: The time limit might be too short for complex solutions\n\n"
                "Try adjusting the objective weights, changing the day, or extending the time window."
            )
    else:
        logger.error("No valid solution found!")
        print("No valid solution found!")


if __name__ == "__main__":
    main() 