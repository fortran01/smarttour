"""Constraint Programming Model for optimizing tourist itineraries.

This module implements a constraint programming model using CPMpy to optimize
tourist itineraries. The model considers multiple objectives and constraints:

Objectives:
    1. Minimize total travel time between venues
    2. Minimize exposure to crowds at venues
    3. Maximize number of venues visited

Constraints:
    1. Time window constraints (venue operating hours)
    2. Travel time constraints between consecutive venues
    3. No overlapping visits
    4. Sequential visit ordering
    5. Dwell time requirements at each venue

The model uses 30-minute time slots and supports flexible tour start/end times.
"""

from typing import Dict, List, Optional, Tuple
from cpmpy import Model
from cpmpy.expressions.variables import IntVar, BoolVar
from cpmpy.solvers import CPM_ortools
import logging

# Set up logger
logger = logging.getLogger(__name__)

# Type alias for days of the week
DayOfWeek = str

# Mapping of day names to integers (0 = Monday, 6 = Sunday)
DAY_TO_INT = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}

class TourOptimizer:
    """Optimizes a day tour itinerary using constraint programming.
    
    This class implements a constraint programming model that optimizes tourist
    itineraries by considering multiple objectives (travel time, crowds, number
    of venues) while respecting various constraints (time windows, travel times,
    dwell times, etc.).
    
    The model uses three types of decision variables:
    1. t[i]: Integer variables for start time slots of each venue
    2. p[i]: Integer variables for position in sequence (0 = not visited)
    3. x[i]: Binary variables for venue selection (1 = selected)
    
    The solver supports multi-threading to improve performance on multi-core
    systems. The number of cores to use can be specified when calling the
    solve() method.
    
    Attributes:
        venues: List of venue names to consider
        n_venues: Number of venues
        dwell_times: Dict mapping venue to dwell time in hours
        time_slots: List of time slots in HH:MM format
        n_slots: Number of time slots
        travel_times: Dict mapping (from,to,time,day) to travel minutes
        crowd_levels: Dict mapping (venue,time,day) to crowd level
        venue_open_slots: Dict mapping (venue,day) to list of valid slots
        tour_start_slot: Index of earliest allowed start slot
        tour_end_slot: Index of latest allowed end slot
        dwell_slots: Dict mapping venue to number of 30-min slots needed
        day: Day of the week for this tour
        model: CPMpy Model instance
        t: Array of IntVar for start time slots
        p: Array of IntVar for positions
        x: Array of BoolVar for venue selection
        w_travel: Weight for travel time
        w_crowd: Weight for crowd levels
        w_venues: Weight for number of venues
        min_venues: Minimum number of venues to visit
    """
    
    def __init__(
        self,
        venues: List[str],
        dwell_times: Dict[str, float],
        time_slots: List[str],  # ["10:00", "10:30", ...]
        travel_times: Dict[
            Tuple[str, str, str, DayOfWeek], int
        ],  # (from,to,time,day)->min
        crowd_levels: Dict[
            Tuple[str, str, DayOfWeek], int
        ],  # (venue,time,day)->level
        venue_open_slots: Optional[
            Dict[Tuple[str, DayOfWeek], List[int]]
        ] = None,  # (venue,day)->slots
        tour_start_time: str = "09:00",  # Earliest tour can start
        tour_end_time: str = "21:00",    # Latest tour must end
        day: DayOfWeek = "Monday",       # Day of the week for tour
    ):
        """Initialize the tour optimizer.
        
        Args:
            venues: List of venue names
            dwell_times: Dictionary mapping venue to dwell time in hours
            time_slots: List of time slots in HH:MM format
            travel_times: Dictionary mapping (from_venue, to_venue, time, day) 
                to travel time in minutes
            crowd_levels: Dictionary mapping (venue, time_slot, day) to 
                crowd level (0-100)
            venue_open_slots: Dictionary mapping (venue, day) to list of valid
                time slot indices (optional)
            tour_start_time: Earliest time the tour can start (HH:MM)
            tour_end_time: Latest time the tour must end (HH:MM)
            day: Day of the week for the tour
        """
        self.venues = venues
        self.n_venues = len(venues)
        self.dwell_times = dwell_times
        self.time_slots = time_slots
        self.n_slots = len(time_slots)
        self.travel_times = travel_times
        self.crowd_levels = crowd_levels
        self.day = day
        
        # Set objective function weights with default values
        self.w_travel = 1.0     # Weight for travel time
        self.w_crowd = 0.5      # Weight for crowd levels
        self.w_venues = -20.0   # Weight for number of venues (negative to maximize)
        
        # Set minimum number of venues to visit (default: 1)
        self.min_venues = 1
        
        # Convert dwell times from hours to number of 30-min slots
        self.dwell_slots = {}
        for venue, hours in dwell_times.items():
            self.dwell_slots[venue] = max(1, int(hours * 2))  # 2 slots per hour
        
        # Convert venue_open_slots to use day-specific slots
        if venue_open_slots:
            self.venue_open_slots = venue_open_slots
        else:
            # Default to all slots being valid for each venue on each day
            self.venue_open_slots = {
                (v, self.day): list(range(self.n_slots)) 
                for v in venues
            }
        
        # Convert tour time window to slot indices
        self.tour_start_slot = time_slots.index(tour_start_time)
        self.tour_end_slot = time_slots.index(tour_end_time)
        
        # Initialize the model
        self.model = Model()
        
        # Create decision variables
        self._create_variables()
        
        # Add constraints
        self._add_constraints()
        
        # Set objective
        self._set_objective()
    
    def _create_variables(self):
        """Create the decision variables for the model."""
        # Integer variables for starting time slots
        self.t = [
            IntVar(0, self.n_slots-1, name=f"start_time_{i}")
            for i in range(self.n_venues)
        ]
        
        # Integer variables for visit order
        self.p = [
            IntVar(0, self.n_venues, name=f"position_{i}")
            for i in range(self.n_venues)
        ]
        
        # Binary variables for venue selection
        self.x = [
            BoolVar(name=f"venue_selected_{i}")
            for i in range(self.n_venues)
        ]
    
    def _add_constraints(self):
        """Add all constraints to the model."""
        # Clear existing constraints to avoid duplicates when updating
        self.model = Model()
        
        # Recreate variables since we reset the model
        self._create_variables()
        
        # Add constraints
        self._add_time_window_constraints()
        self._add_sequence_constraints()
        self._add_overlap_constraints()
        
        # Reset objective with current weights
        self._set_objective()
    
    def _add_time_window_constraints(self):
        """Add constraints for time windows.
        
        This method adds constraints to ensure:
        1. Visits start within the overall tour window
        2. Visits start and end within venue-specific operating hours
        3. All time slots during a visit are within valid operating hours
        """
        for i, venue in enumerate(self.venues):
            # Get valid slots for this venue on this day
            valid_slots = self.venue_open_slots.get((venue, self.day), [])
            
            if valid_slots:
                # Get earliest and latest valid slots
                earliest_valid = min(valid_slots)
                latest_valid = max(valid_slots)
                
                # Calculate latest possible start time that allows full visit within opening hours
                latest_start = (
                    latest_valid - self.dwell_slots[venue] + 1
                )
                
                # 1. If venue is selected, start time must be within valid range
                self.model += self.x[i].implies(
                    (self.t[i] >= max(self.tour_start_slot, earliest_valid)) &
                    (self.t[i] <= min(self.tour_end_slot, latest_start))
                )
                
                # 2. Ensure end time is within valid slots
                self.model += self.x[i].implies(
                    self.t[i] + self.dwell_slots[venue] <= latest_valid + 1
                )
                
                # 3. For each potential start time, ensure all visit slots are valid
                for t in range(self.n_slots):
                    # Calculate visit slots for this start time
                    visit_end = t + self.dwell_slots[venue]
                    visit_slots = list(range(t, visit_end))
                    
                    # If any visit slot is invalid, this start time is not allowed
                    if not all(slot in valid_slots for slot in visit_slots):
                        self.model += self.x[i].implies(self.t[i] != t)
            else:
                # If no valid slots, venue cannot be selected
                self.model += ~self.x[i]
    
    def _add_sequence_constraints(self):
        """Add constraints for sequential visit ordering.
        
        This method adds constraints to ensure:
        1. Each selected venue has a unique position in sequence
        2. Positions are consecutive starting from 1
        3. Travel times between consecutive venues are respected
        4. Visits respect venue closing times when considering 
           travel between venues
        """
        # 1. Each selected venue has a unique position
        for i in range(self.n_venues):
            # If venue is selected, position must be > 0
            self.model += self.x[i].implies(self.p[i] > 0)
            # If venue is not selected, position must be 0
            self.model += (~self.x[i]).implies(self.p[i] == 0)
        
        # 2. Positions must be consecutive starting from 1
        # First, count how many venues are selected
        n_selected = sum(self.x)
        
        # Store the count as an instance variable for use elsewhere
        self.n_selected = n_selected
        
        # Log the count
        logger.info(f"Number of selected venues: {n_selected}")
        
        # Allow the optimizer to select at least min_venues venues
        self.model += n_selected >= self.min_venues
        
        # Then ensure positions are 1..n_selected
        for i in range(self.n_venues):
            for pos in range(1, self.n_venues + 1):
                # If venue i has position pos, pos must be <= n_selected
                self.model += (self.p[i] == pos).implies(pos <= n_selected)
        
        # Each position from 1 to n_selected must be used exactly once
        for pos in range(1, self.n_venues + 1):
            # Count how many venues have this position
            pos_count = sum(self.p[i] == pos for i in range(self.n_venues))
            # If pos <= n_selected, exactly one venue must have this position
            self.model += (pos <= n_selected).implies(pos_count == 1)
            # If pos > n_selected, no venue can have this position
            self.model += (pos > n_selected).implies(pos_count == 0)
        
        # 3 & 4. Add travel time and closing time constraints
        for i in range(self.n_venues):
            venue_i = self.venues[i]
            # Get valid slots for venue i
            valid_slots_i = self.venue_open_slots.get((venue_i, self.day), [])
            if not valid_slots_i:
                continue
                
            latest_valid_i = max(valid_slots_i)
            dwell_i = self.dwell_slots[venue_i]
            
            for j in range(self.n_venues):
                if i == j:
                    continue
                    
                venue_j = self.venues[j]
                # Get valid slots for venue j
                valid_slots_j = self.venue_open_slots.get(
                    (venue_j, self.day), []
                )
                if not valid_slots_j:
                    continue
                    
                latest_valid_j = max(valid_slots_j)
                dwell_j = self.dwell_slots[venue_j]
                
                # If j follows i directly
                is_consecutive = (self.p[j] == self.p[i] + 1)
                both_selected = self.x[i] & self.x[j]
                
                # For each possible end time of venue i
                for slot_idx in range(self.n_slots):
                    # If venue i starts at this slot
                    i_starts_at_slot = (self.t[i] == slot_idx)
                    
                    # Calculate when venue i would end
                    i_end_slot = slot_idx + dwell_i
                    
                    # If i would end after closing, this start time not allowed
                    if i_end_slot > latest_valid_i:
                        self.model += ~(self.x[i] & i_starts_at_slot)
                        continue
                    
                    # Get travel time from i to j at this end time
                    if i_end_slot < len(self.time_slots):
                        end_time = self.time_slots[i_end_slot]
                        travel_key = (
                            venue_i, venue_j, end_time, self.day
                        )
                        
                        if travel_key in self.travel_times:
                            travel_time = self.travel_times[travel_key]
                            # Convert minutes to slots (round up)
                            travel_slots = (travel_time + 29) // 30
                            
                            # j must start after i ends plus travel time
                            # AND j must end before its closing time
                            j_earliest_start = i_end_slot + travel_slots
                            j_latest_start = latest_valid_j - dwell_j
                            
                            # If consecutive and i starts at slot_idx,
                            # j must start in valid window
                            self.model += ~(
                                both_selected & 
                                is_consecutive & 
                                i_starts_at_slot
                            ) | (
                                (self.t[j] >= j_earliest_start) &
                                (self.t[j] <= j_latest_start)
                            )
    
    def _add_overlap_constraints(self):
        """Add constraints to prevent time slot overlaps."""
        # For each pair of venues
        for i in range(self.n_venues):
            for j in range(i + 1, self.n_venues):
                # Only need constraint if both venues are selected
                both_selected = self.x[i] & self.x[j]
                
                # Get dwell times for both venues
                dwell_i = self.dwell_slots[self.venues[i]]
                dwell_j = self.dwell_slots[self.venues[j]]
                
                # Either:
                # 1. i ends before j starts: t[i] + dwell_i <= t[j]
                # 2. j ends before i starts: t[j] + dwell_j <= t[i]
                # 3. One of them is not selected: ~both_selected
                self.model += (
                    ~both_selected | 
                    (self.t[i] + dwell_i <= self.t[j]) | 
                    (self.t[j] + dwell_j <= self.t[i])
                )
                
                # Also ensure that if both are selected, they have different positions
                self.model += ~both_selected | (self.p[i] != self.p[j])
                
                # Add travel time constraints for consecutive venues
                for slot_idx, slot_time in enumerate(self.time_slots):
                    # If i starts at this slot
                    i_starts_at_slot = (self.t[i] == slot_idx)
                    
                    # Get travel time from i to j at this time
                    travel_key = (
                        self.venues[i],
                        self.venues[j],
                        slot_time,
                        self.day
                    )
                    if travel_key in self.travel_times:
                        travel_time = self.travel_times[travel_key]
                        # Convert minutes to 30-min slots (round up)
                        travel_slots = (travel_time + 29) // 30
                        
                        # If j follows i, ensure enough time for travel
                        is_consecutive = (self.p[j] == self.p[i] + 1)
                        
                        # If i is selected, j follows i, and i starts at slot_idx,
                        # then j must start after i ends plus travel time
                        self.model += ~(
                            both_selected & 
                            is_consecutive & 
                            i_starts_at_slot
                        ) | (
                            self.t[j] >= self.t[i] + dwell_i + travel_slots
                        )
    
    def _set_objective(self):
        """Set the multi-objective optimization function.
        
        The objective combines three components with weights:
        1. Total travel time between consecutive venues
        2. Total crowd exposure during visits
        3. Number of venues visited (negative to maximize)
        
        Components are normalized to similar scales:
        - Travel time divided by max possible travel time
        - Crowd levels divided by max possible crowd level
        - Number of venues divided by total venues
        """
        # 1. Calculate total travel time between consecutive venues
        total_travel_time = 0
        for pos in range(1, self.n_venues):
            for i in range(self.n_venues):
                for j in range(self.n_venues):
                    # If venue i is at position pos and venue j at pos-1
                    is_consecutive = (
                        (self.p[i] == pos + 1) & 
                        (self.p[j] == pos)
                    )
                    
                    # For each possible time slot
                    for slot_idx, slot_time in enumerate(self.time_slots):
                        # If j starts at this slot
                        starts_at_slot = (self.t[j] == slot_idx)
                        if starts_at_slot:
                            # Get travel time from j to i at this time
                            travel_key = (
                                self.venues[j],
                                self.venues[i],
                                slot_time,
                                self.day
                            )
                            if travel_key in self.travel_times:
                                travel_time = self.travel_times[travel_key]
                                total_travel_time += (
                                    is_consecutive & starts_at_slot
                                ) * travel_time
        
        # 2. Calculate total crowd exposure during visits
        total_crowd_level = 0
        max_crowd_level = 100  # Crowd levels are 0-100
        for i, venue in enumerate(self.venues):
            # For each selected venue
            if self.x[i]:
                dwell = self.dwell_slots[venue]
                # For each possible time slot
                for slot_idx, slot_time in enumerate(self.time_slots):
                    # If venue starts at this slot
                    starts_at_slot = (self.t[i] == slot_idx)
                    if starts_at_slot:
                        # Sum crowd levels for all time slots during visit
                        for offset in range(dwell):
                            visit_slot_idx = slot_idx + offset
                            if visit_slot_idx < self.n_slots:
                                visit_slot_time = self.time_slots[visit_slot_idx]
                                crowd_key = (venue, visit_slot_time, self.day)
                                if crowd_key in self.crowd_levels:
                                    crowd_level = self.crowd_levels[crowd_key]
                                    total_crowd_level += (
                                        starts_at_slot & self.x[i]
                                    ) * crowd_level
        
        # 3. Count number of venues visited (to maximize)
        n_visited = sum(self.x)
        
        # Calculate maximum possible travel time for normalization
        max_travel_time = max(
            [time for time in self.travel_times.values()],
            default=1  # Default to 1 if no travel times
        )
        
        # Normalize components (avoid division by zero)
        normalized_travel = total_travel_time / max(1, max_travel_time)
        normalized_crowd = total_crowd_level / max(1, max_crowd_level * self.n_venues * self.n_slots)
        normalized_venues = n_visited / max(1, self.n_venues)
        
        # Combine objectives with weights
        objective = 0
        objective += self.w_travel * normalized_travel   # Minimize travel time
        objective += self.w_crowd * normalized_crowd     # Minimize crowd levels
        objective += self.w_venues * normalized_venues   # Maximize venues
        
        self.model.minimize(objective)
    
    def solve(self, num_cores: int = 4, time_limit: int = 300) -> Optional[Dict]:
        """Solve the model and return the solution if found.
        
        Args:
            num_cores: Number of CPU cores to use for parallel solving (default: 4)
            time_limit: Time limit in seconds for the solver (default: 300)
        
        Returns:
            Dict containing the solution details if found:
            - selected_venues: List of selected venues in visit order
            - start_times: Dict mapping venue to start time
            - metrics: Dict of optimization metrics
            - schedule: List of dicts with detailed timing
            Returns None if no solution is found.
        """
        logger = logging.getLogger(__name__)
        logger.info("Starting optimization...")
        
        try:
            # Create a new solver instance
            solver = CPM_ortools(self.model)
            
            # Attempt to solve the model
            if solver.solve():
                logger.info("Solution found successfully")
                return self._format_solution()
            else:
                logger.warning("No solution found within constraints")
                return None
                
        except Exception as e:
            logger.error(f"Error during optimization: {str(e)}")
            return None
    
    def _format_solution(self) -> Dict:
        """Format the solution into a readable dictionary."""
        logger = logging.getLogger(__name__)
        
        # Get solution values - use the value() method on the variables
        x_val = [bool(x.value()) for x in self.x]
        t_val = [int(t.value()) for t in self.t]
        p_val = [int(p.value()) for p in self.p]
        
        # Create ordered list of selected venues
        selected_indices = [i for i in range(self.n_venues) if x_val[i]]
        ordered_indices = sorted(selected_indices, key=lambda i: p_val[i])
        selected_venues = [self.venues[i] for i in ordered_indices]
        
        # Create schedule with detailed timing
        schedule = []
        total_travel_time = 0
        total_crowd_level = 0
        
        # Track the current time slot to ensure travel times are respected
        current_time_slot = None
        
        logger.info("=== Detailed Schedule Validation ===")
        
        for idx, venue_idx in enumerate(ordered_indices):
            venue = self.venues[venue_idx]
            logger.info(f"\nProcessing venue: {venue}")
            
            # Get the solver's assigned start slot
            solver_start_slot = t_val[venue_idx]
            logger.info(f"Solver assigned start slot: {solver_start_slot} ({self.time_slots[solver_start_slot]})")
            
            # Get valid slots for this venue
            valid_slots = self.venue_open_slots.get((venue, self.day), [])
            if valid_slots:
                opening_slot = min(valid_slots)
                closing_slot = max(valid_slots)
                logger.info(f"Valid slots: opens={self.time_slots[opening_slot]}, closes={self.time_slots[closing_slot]}")
            else:
                logger.warning(f"No valid slots found for {venue} on {self.day}")
            
            # For the first venue, use the solver's assigned start slot
            if idx == 0:
                start_slot = solver_start_slot
                current_time_slot = start_slot
                logger.info("First venue - using solver's start slot")
            else:
                # For subsequent venues, ensure travel time from previous venue is respected
                prev_venue_idx = ordered_indices[idx-1]
                prev_venue = self.venues[prev_venue_idx]
                prev_end_slot = t_val[prev_venue_idx] + self.dwell_slots[prev_venue]
                
                # Get travel time from previous venue to this venue
                prev_end_time = self.time_slots[min(prev_end_slot, self.n_slots - 1)]
                travel_key = (prev_venue, venue, prev_end_time, self.day)
                
                logger.info(f"Previous venue {prev_venue} ends at: {prev_end_time}")
                
                if travel_key in self.travel_times:
                    travel_time = self.travel_times[travel_key]
                    # Convert travel time to slots (round up)
                    travel_slots = (travel_time + 29) // 30
                    logger.info(f"Travel time from {prev_venue}: {travel_time} minutes ({travel_slots} slots)")
                    
                    # Calculate the earliest possible start slot after travel
                    earliest_start_after_travel = prev_end_slot + travel_slots
                    
                    # Ensure we don't exceed available time slots
                    if earliest_start_after_travel >= len(self.time_slots):
                        logger.error(
                            f"Cannot schedule {venue} after {prev_venue} - "
                            f"would exceed available time slots"
                        )
                        continue
                    
                    logger.info(
                        f"Earliest possible start after travel: "
                        f"{self.time_slots[earliest_start_after_travel]}"
                    )
                    
                    # Use the maximum of the solver's assigned start slot 
                    # and the earliest possible start
                    start_slot = max(solver_start_slot, earliest_start_after_travel)
                    
                    # Verify start_slot is valid
                    if start_slot >= len(self.time_slots):
                        logger.error(
                            f"Cannot schedule {venue} - start time would be "
                            f"after available time slots"
                        )
                        continue
                else:
                    # If no travel time data, use solver's assigned start slot
                    # but ensure it's after previous venue ends
                    start_slot = max(solver_start_slot, prev_end_slot + 1)
                
                # Update current time slot
                current_time_slot = start_slot
            
            # Check if the venue is still open at the adjusted start time
            dwell_slots = self.dwell_slots[venue]
            end_slot = start_slot + dwell_slots
            
            # Validate end_slot is within bounds
            if end_slot >= len(self.time_slots):
                logger.error(f"Visit to {venue} would end after available time slots. Start: {self.time_slots[start_slot]}, Duration: {self.dwell_times[venue]} hours")
                continue
                
            logger.info(f"Final scheduled time: {self.time_slots[start_slot]} - {self.time_slots[end_slot]}")
            logger.info(f"Dwell time: {self.dwell_times[venue]} hours ({dwell_slots} slots)")
            
            # Check if the entire visit is within valid slots
            visit_slots = range(start_slot, end_slot)
            is_valid_visit = all(slot in valid_slots for slot in visit_slots)
            
            if not is_valid_visit:
                invalid_slots = [slot for slot in visit_slots if slot not in valid_slots]
                logger.error(f"Invalid visit slots: {[self.time_slots[slot] for slot in invalid_slots]}")
                
                # Find the venue's closing time
                if valid_slots:
                    closing_slot = max(valid_slots)
                    closing_time = self.time_slots[closing_slot]
                    logger.error(f"Visit extends past closing time ({closing_time})")
                    warning = f"Warning: Visit extends past closing time ({closing_time})"
                else:
                    logger.error(f"Venue may be closed on {self.day}")
                    warning = "Warning: Venue may be closed on this day"
            else:
                warning = None
                logger.info("Visit time is valid within operating hours")
            
            # Get the start time string
            start_time = self.time_slots[min(start_slot, self.n_slots - 1)]
            
            # Calculate end time
            end_time = self.time_slots[min(end_slot, self.n_slots - 1)]
            
            # Calculate crowd levels during visit
            crowd_levels = []
            for slot in range(start_slot, min(end_slot, self.n_slots)):
                crowd_key = (venue, self.time_slots[slot], self.day)
                if crowd_key in self.crowd_levels:
                    crowd_levels.append(self.crowd_levels[crowd_key])
            avg_crowd = (
                sum(crowd_levels) / len(crowd_levels) 
                if crowd_levels else 0
            )
            total_crowd_level += sum(crowd_levels)
            
            # Calculate travel time to next venue if not last
            travel_time = None
            if idx < len(ordered_indices) - 1:
                next_venue_idx = ordered_indices[idx + 1]
                next_venue = self.venues[next_venue_idx]
                travel_key = (
                    venue,
                    next_venue,
                    end_time,
                    self.day
                )
                if travel_key in self.travel_times:
                    travel_time = self.travel_times[travel_key]
                    total_travel_time += travel_time
            
            visit = {
                "venue": venue,
                "start_time": start_time,
                "end_time": end_time,
                "dwell_time_hours": self.dwell_times[venue],
                "crowd_level_avg": avg_crowd,
                "travel_time_to_next": travel_time,
                "warning": warning
            }
            schedule.append(visit)
        
        # Compute metrics
        metrics = {
            "total_venues": len(selected_venues),
            "total_travel_time_minutes": total_travel_time,
            "average_travel_time": (
                total_travel_time / (len(selected_venues) - 1)
                if len(selected_venues) > 1 else 0
            ),
            "total_crowd_exposure": total_crowd_level,
            "average_crowd_level": (
                total_crowd_level / 
                sum(self.dwell_slots[v] for v in selected_venues)
                if selected_venues else 0
            )
        }
        
        logger.info("\n=== Schedule Validation Complete ===")
        
        # Create a mapping of venues to their adjusted start times
        adjusted_start_times = {
            visit["venue"]: visit["start_time"] for visit in schedule
        }
        
        return {
            "selected_venues": selected_venues,
            "start_times": adjusted_start_times,
            "metrics": metrics,
            "schedule": schedule
        }

    def set_objective_weights(
        self, 
        travel_weight: float = 1.0, 
        crowd_weight: float = 0.5, 
        venues_weight: float = -20.0
    ):
        """Set the weights for the multi-objective optimization function.
        
        Args:
            travel_weight: Weight for travel time minimization (default: 1.0)
            crowd_weight: Weight for crowd level minimization (default: 0.5)
            venues_weight: Weight for venue count maximization (default: -20.0,
                negative to maximize)
        """
        self.w_travel = travel_weight
        self.w_crowd = crowd_weight
        self.w_venues = venues_weight
        
        # Re-set the objective with the new weights
        self._set_objective()
        
        return self 

    def set_min_venues(self, min_venues: int) -> 'TourOptimizer':
        """Set the minimum number of venues to visit.
        
        Args:
            min_venues: Minimum number of venues to visit (must be >= 1)
            
        Returns:
            Self for method chaining
        """
        self.min_venues = max(1, min_venues)  # Ensure at least 1
        
        # Rebuild the entire model with the new minimum
        self._add_constraints()
        
        return self 