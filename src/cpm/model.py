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

from typing import Dict, List, Optional, Tuple, Literal
from cpmpy import Model
from cpmpy.expressions.variables import IntVar, BoolVar

# Type alias for days of the week
DayOfWeek = Literal[
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday"
]

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
        self._add_time_window_constraints()
        self._add_sequence_constraints()
        self._add_overlap_constraints()
    
    def _add_time_window_constraints(self):
        """Add constraints for time windows and operating hours.
        
        This method adds three types of time window constraints:
        1. Venue-specific operating hours for the given day
        2. Tour-wide time window (start/end times)
        3. Valid time slots for each venue's entire visit duration
        
        For each venue i:
        - If selected (x[i] = 1):
            * Start time must be in valid slots for the given day
            * Entire visit must be within valid slots
            * Visit must end before closing time
        - If not selected (x[i] = 0):
            * No constraints on time variables
        """
        # First, add venue-specific time window constraints
        for i, venue in enumerate(self.venues):
            # Get valid time slots for this venue on this day
            valid_slots = self.venue_open_slots.get(
                (venue, self.day),
                list(range(self.n_slots))  # Default if not specified
            )
            dwell = self.dwell_slots[venue]
            
            # If venue is selected (x[i] = 1):
            # 1. Start time must be in valid slots for this day
            if valid_slots:  # Only add constraint if we have valid slots
                # Create a disjunction of valid start times
                valid_starts = [self.t[i] == slot for slot in valid_slots]
                # Add constraint: if venue is selected, start time must be valid
                self.model += self.x[i].implies(any(valid_starts))
            
            # 2. Entire visit (start + dwell) must be within valid slots
            # For each possible start time, check if all slots until dwell 
            # time are valid
            for start in range(self.n_slots):
                visit_slots = range(start, min(start + dwell, self.n_slots))
                # A start time is valid if all slots during visit are valid
                is_valid_start = all(slot in valid_slots for slot in visit_slots)
                if not is_valid_start:
                    # If any slot in the visit duration is invalid,
                    # this start time is not allowed if venue is selected
                    self.model += self.x[i].implies(self.t[i] != start)
            
            # 3. Visit must end before closing time
            # Find the last valid slot for this venue
            if valid_slots:
                last_valid_slot = max(valid_slots)
                self.model += self.x[i].implies(
                    self.t[i] + dwell <= last_valid_slot + 1
                )
            else:
                # If no valid slots specified, use general closing time
                self.model += self.x[i].implies(
                    self.t[i] + dwell <= self.n_slots
                )
        
        # Add tour-wide time window constraints
        for i in range(self.n_venues):
            # Selected venues must start after tour_start_time
            self.model += self.x[i].implies(
                self.t[i] >= self.tour_start_slot
            )
            
            # Selected venues must end before tour_end_time
            self.model += self.x[i].implies(
                self.t[i] + self.dwell_slots[self.venues[i]] <= 
                self.tour_end_slot
            )
        
        # Ensure first venue starts after tour_start_time
        first_venue_constraints = [
            (self.p[i] == 1).implies(self.t[i] >= self.tour_start_slot)
            for i in range(self.n_venues)
        ]
        self.model += any(first_venue_constraints)
        
        # Ensure last venue ends before tour_end_time
        last_venue_constraints = [
            (self.p[i] == sum(self.x)).implies(
                self.t[i] + self.dwell_slots[self.venues[i]] <= 
                self.tour_end_slot
            )
            for i in range(self.n_venues)
        ]
        self.model += any(last_venue_constraints)
    
    def _add_sequence_constraints(self):
        """Add constraints for sequential visit ordering.
        
        This method adds constraints to ensure:
        1. Each selected venue has a unique position in sequence
        2. Positions are consecutive starting from 1
        3. Travel times between consecutive venues are respected
        4. No overlapping visits
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
        
        # Allow the optimizer to select any number of venues
        # This enables skipping venues that are closed on the selected day
        # We still want to visit at least one venue
        self.model += n_selected >= 1
        
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
        
        # 3. Travel times between consecutive venues must be respected
        for i in range(self.n_venues):
            for j in range(self.n_venues):
                if i != j:
                    # If venue j follows venue i in sequence
                    follows = (self.p[j] == self.p[i] + 1)
                    
                    # For each possible time slot
                    for slot_idx, slot_time in enumerate(self.time_slots):
                        # If i starts at this slot
                        i_starts_at = (self.t[i] == slot_idx)
                        if i_starts_at:
                            # Get travel time from i to j
                            travel_key = (
                                self.venues[i],
                                self.venues[j],
                                slot_time,
                                self.day
                            )
                            travel_time = self.travel_times.get(
                                travel_key,
                                30  # Default 30 minutes if not specified
                            )
                            # Convert travel time to number of slots
                            travel_slots = (travel_time + 29) // 30
                            # j must start after i ends plus travel time
                            self.model += (follows & i_starts_at).implies(
                                self.t[j] >= slot_idx + 
                                self.dwell_slots[self.venues[i]] +
                                travel_slots
                            )
        
        # 4. No overlapping visits
        for i in range(self.n_venues):
            for j in range(i + 1, self.n_venues):
                # If both venues are selected
                both_selected = self.x[i] & self.x[j]
                # They must not overlap in time
                self.model += both_selected.implies(
                    (self.t[i] + self.dwell_slots[self.venues[i]] <= 
                     self.t[j]) |
                    (self.t[j] + self.dwell_slots[self.venues[j]] <= 
                     self.t[i])
                )
    
    def _add_overlap_constraints(self):
        """Add constraints to prevent time slot overlaps.
        
        This method ensures that no two venues can be visited at the same time.
        For each pair of venues i,j:
        1. Either i ends before j starts
        2. Or j ends before i starts
        3. Or at least one is not selected
        
        Also adds constraints to ensure:
        - Selected venues have different positions
        - Consecutive venues respect travel times
        """
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
                
                # And ensure that consecutive venues respect travel times
                for slot_idx, slot_time in enumerate(self.time_slots):
                    # If i starts at this slot
                    i_starts_at_slot = (self.t[i] == slot_idx)
                    if i_starts_at_slot:
                        # Get travel time from i to j
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
                            is_consecutive = (
                                (self.p[j] == self.p[i] + 1)
                            )
                            self.model += ~(
                                both_selected & 
                                i_starts_at_slot & 
                                is_consecutive
                            ) | (
                                self.t[j] >= 
                                self.t[i] + dwell_i + travel_slots
                            )
    
    def _set_objective(self):
        """Set the multi-objective optimization function.
        
        The objective combines three components with weights:
        1. Total travel time between consecutive venues
        2. Total crowd exposure during visits
        3. Number of venues visited (negative to maximize)
        
        Components are normalized to similar scales:
        - Travel time divided by 30 (assuming ~30 min average)
        - Crowd levels divided by 100 (0-100 scale)
        - Number of venues used directly with negative weight
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
        
        # Combine objectives with weights
        # Note: Convert n_visited to negative since we're minimizing
        # Use the instance attributes for weights instead of hardcoded values
        
        # Normalize the components to similar scales
        # Assuming:
        # - Average travel time is 30 mins
        # - Crowd level is 0-100 scale
        # - Number of venues is normalized by max possible venues
        normalized_travel = total_travel_time / 30
        normalized_crowd = total_crowd_level / 100
        normalized_venues = n_visited / self.n_venues  # Normalize by total possible venues
        
        objective = (
            self.w_travel * normalized_travel +
            self.w_crowd * normalized_crowd +
            self.w_venues * normalized_venues
        )
        
        self.model.minimize(objective)
    
    def solve(self) -> Optional[Dict]:
        """Solve the model and return the solution if found.
        
        Returns:
            Dict containing the solution details if found:
            - selected_venues: List of selected venues in visit order
            - start_times: Dict mapping venue to start time
            - metrics: Dict of optimization metrics
            - schedule: List of dicts with detailed timing
            Returns None if no solution is found.
        """
        if self.model.solve():
            # TODO: Format solution
            return self._format_solution()
        return None
    
    def _format_solution(self) -> Dict:
        """Format the solution into a readable dictionary.
        
        This method takes the raw solution values and formats them into a
        user-friendly dictionary containing:
        - selected_venues: List of selected venues in visit order
        - start_times: Dict mapping venue to start time
        - metrics: Dict of optimization metrics (travel time, crowd level)
        - schedule: List of dicts with detailed timing for each visit
        
        The schedule includes for each visit:
        - venue: Name of the venue
        - start_time: Start time in HH:MM format
        - end_time: End time in HH:MM format
        - dwell_time_hours: Time spent at venue
        - crowd_level_avg: Average crowd level during visit
        - travel_time_to_next: Travel time to next venue (if any)
        
        Returns:
            Dict containing the formatted solution
        """
        # Get solution values
        x_val = [bool(self.x[i].value()) for i in range(self.n_venues)]
        t_val = [int(self.t[i].value()) for i in range(self.n_venues)]
        p_val = [int(self.p[i].value()) for i in range(self.n_venues)]
        
        # Create ordered list of selected venues
        selected_indices = [i for i in range(self.n_venues) if x_val[i]]
        ordered_indices = sorted(selected_indices, key=lambda i: p_val[i])
        selected_venues = [self.venues[i] for i in ordered_indices]
        
        # Create schedule with detailed timing
        schedule = []
        total_travel_time = 0
        total_crowd_level = 0
        
        for idx, venue_idx in enumerate(ordered_indices):
            venue = self.venues[venue_idx]
            start_slot = t_val[venue_idx]
            start_time = self.time_slots[start_slot]
            dwell_slots = self.dwell_slots[venue]
            
            # Calculate end time
            end_slot = start_slot + dwell_slots
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
                "travel_time_to_next": travel_time
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
        
        return {
            "selected_venues": selected_venues,
            "start_times": {
                self.venues[i]: self.time_slots[t_val[i]]
                for i in selected_indices
            },
            "metrics": metrics,
            "schedule": schedule
        } 