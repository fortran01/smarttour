"""Pareto Optimality Analysis for the Tour Optimization Model.

This module implements a Pareto Optimality Analysis for the TourOptimizer model.
It generates multiple solutions by varying the weights in the objective function,
identifies the Pareto-optimal solutions, and visualizes the Pareto front.

The analysis focuses on three objectives:
1. Minimize total travel time between venues
2. Minimize exposure to crowds at venues
3. Maximize number of venues visited

The Pareto front shows the trade-offs between these competing objectives.
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import pandas as pd
import concurrent.futures
from .model import TourOptimizer
from .data_loader import DataLoader
from .optimize_tour import generate_time_slots


def generate_weight_combinations(
    n_points: int = 10
) -> List[Tuple[float, float, float]]:
    """Generate different weight combinations for the objective function.
    
    Args:
        n_points: Number of points to generate for each weight
    
    Returns:
        List of (w_travel, w_crowd, w_venues) weight combinations
        Note: w_venues is negative to maximize number of venues
    """
    # Generate positive weights between 0.1 and 1.0 for travel and crowd
    positive_weights = np.linspace(0.1, 1.0, n_points)

    # We use negative weights because we want to maximize venues
    negative_weights = np.linspace(-1, -20, n_points)
    
    # Generate all combinations of weights
    combinations = []
    for w_travel in positive_weights:
        for w_crowd in positive_weights:
            for w_venues in negative_weights:
                combinations.append((w_travel, w_crowd, w_venues))
    
    return combinations


def is_pareto_optimal(
    solution: Dict,
    all_solutions: List[Dict]
) -> bool:
    """Check if a solution is Pareto-optimal (non-dominated).
    
    A solution is Pareto-optimal if no other solution is better in all objectives.
    
    Args:
        solution: The solution to check
        all_solutions: List of all solutions to compare against
    
    Returns:
        True if the solution is Pareto-optimal, False otherwise
    """
    # Extract metrics for the current solution
    metrics = solution["metrics"]
    travel_time = metrics["total_travel_time_minutes"]
    crowd_level = metrics["average_crowd_level"]
    venues_visited = metrics["total_venues"]
    
    # Check if any other solution dominates this one
    for other in all_solutions:
        if other is solution:
            continue
        
        other_metrics = other["metrics"]
        other_travel = other_metrics["total_travel_time_minutes"]
        other_crowd = other_metrics["average_crowd_level"]
        other_venues = other_metrics["total_venues"]
        
        # Check if other solution is better in all objectives
        # Note: For venues_visited, higher is better, so we check if other_venues > venues_visited
        if (other_travel <= travel_time and 
            other_crowd <= crowd_level and 
            other_venues >= venues_visited and
            (other_travel < travel_time or 
             other_crowd < crowd_level or 
             other_venues > venues_visited)):
            return False
    
    return True


def identify_pareto_optimal_solutions(
    solutions: List[Dict]
) -> List[Dict]:
    """Identify Pareto-optimal solutions from a list of solutions.
    
    Args:
        solutions: List of solutions
    
    Returns:
        List of Pareto-optimal solutions
    """
    return [s for s in solutions if is_pareto_optimal(s, solutions)]


def visualize_pareto_front(
    solutions: List[Dict],
    pareto_solutions: List[Dict],
    output_path: Optional[str] = None
):
    """Visualize the Pareto front in 3D.
    
    Args:
        solutions: List of all solutions
        pareto_solutions: List of Pareto-optimal solutions
        output_path: Path to save the plot (optional)
    """
    # Extract metrics for all solutions
    all_travel = [s["metrics"]["total_travel_time_minutes"] for s in solutions]
    all_crowd = [s["metrics"]["average_crowd_level"] for s in solutions]
    all_venues = [s["metrics"]["total_venues"] for s in solutions]
    
    # Extract metrics for Pareto-optimal solutions
    pareto_travel = [s["metrics"]["total_travel_time_minutes"] for s in pareto_solutions]
    pareto_crowd = [s["metrics"]["average_crowd_level"] for s in pareto_solutions]
    pareto_venues = [s["metrics"]["total_venues"] for s in pareto_solutions]
    
    # Create 3D plot
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Plot all solutions
    ax.scatter(
        all_travel, all_crowd, all_venues,
        c='blue', marker='o', alpha=0.3, label='All Solutions'
    )
    
    # Plot Pareto-optimal solutions
    ax.scatter(
        pareto_travel, pareto_crowd, pareto_venues,
        c='red', marker='o', s=100, label='Pareto-Optimal Solutions'
    )
    
    # Add labels and title
    ax.set_xlabel('Travel Time (minutes)')
    ax.set_ylabel('Average Crowd Level')
    ax.set_zlabel('Number of Venues Visited')
    ax.set_title('Pareto Front for Tour Optimization')
    
    # Add legend
    ax.legend()
    
    # Save or show the plot
    if output_path:
        plt.savefig(output_path)
    else:
        plt.show()
    
    # Create 2D plots for each pair of objectives
    fig, axs = plt.subplots(1, 3, figsize=(18, 6))
    
    # Travel Time vs Crowd Level
    axs[0].scatter(all_travel, all_crowd, c='blue', alpha=0.3)
    axs[0].scatter(pareto_travel, pareto_crowd, c='red', s=100)
    axs[0].set_xlabel('Travel Time (minutes)')
    axs[0].set_ylabel('Average Crowd Level')
    axs[0].set_title('Travel Time vs Crowd Level')
    
    # Travel Time vs Venues Visited
    axs[1].scatter(all_travel, all_venues, c='blue', alpha=0.3)
    axs[1].scatter(pareto_travel, pareto_venues, c='red', s=100)
    axs[1].set_xlabel('Travel Time (minutes)')
    axs[1].set_ylabel('Number of Venues Visited')
    axs[1].set_title('Travel Time vs Venues Visited')
    
    # Crowd Level vs Venues Visited
    axs[2].scatter(all_crowd, all_venues, c='blue', alpha=0.3)
    axs[2].scatter(pareto_crowd, pareto_venues, c='red', s=100)
    axs[2].set_xlabel('Average Crowd Level')
    axs[2].set_ylabel('Number of Venues Visited')
    axs[2].set_title('Crowd Level vs Venues Visited')
    
    plt.tight_layout()
    
    # Save or show the 2D plots
    if output_path:
        base_path = output_path.rsplit('.', 1)[0]
        plt.savefig(f"{base_path}_2d.png")
    else:
        plt.show()


def run_model_with_weights(
    data_loader: DataLoader,
    venues: List[str],
    time_slots: List[str],
    day: str,
    w_travel: float,
    w_crowd: float,
    w_venues: float,
    i: Optional[int] = None,
    total: Optional[int] = None
) -> Optional[Dict]:
    """Run the model with specific weights for the objective function.
    
    Args:
        data_loader: DataLoader instance
        venues: List of venue names
        time_slots: List of time slots
        day: Day of the week
        w_travel: Weight for travel time
        w_crowd: Weight for crowd levels
        w_venues: Weight for number of venues (negative to maximize)
        i: Optional index for progress reporting
        total: Optional total count for progress reporting
    
    Returns:
        Solution dictionary if found, None otherwise
    """
    # Print progress if index is provided
    if i is not None and total is not None:
        print(
            f"Running model with weights ({w_travel:.2f}, {w_crowd:.2f}, "
            f"{w_venues:.2f}) [{i+1}/{total}]"
        )
    
    # Load all required data
    (
        venue_data,
        dwell_times,
        travel_times,
        crowd_levels,
        venue_open_slots
    ) = data_loader.load_all(time_slots)
    
    # Create a new optimizer instance for this run
    optimizer = TourOptimizer(
        venues=venues,
        dwell_times=dwell_times,
        time_slots=time_slots,
        travel_times=travel_times,
        crowd_levels=crowd_levels,
        venue_open_slots=venue_open_slots,
        tour_start_time="09:00",
        tour_end_time="22:30",
        day=day
    )
    
    # Set minimum number of venues to visit
    optimizer.set_min_venues(3)
    
    # Set custom weights for the objective function
    # Note: w_venues is already negative to maximize venues
    optimizer.w_travel = w_travel
    optimizer.w_crowd = w_crowd
    # Use w_venues directly since it's already negative
    optimizer.w_venues = w_venues
    
    # Solve the model
    solution = optimizer.solve()
    
    # Add weights to solution for reference if solution exists
    if solution:
        solution["weights"] = {
            "w_travel": w_travel,
            "w_crowd": w_crowd,
            "w_venues": w_venues
        }
    
    return solution


# Worker function for parallel execution
def worker_run_model(args):
    """Worker function for parallel execution of run_model_with_weights.
    
    Args:
        args: Tuple containing (i, weights, data_loader, venues, time_slots, 
              day, total)
    
    Returns:
        Result from run_model_with_weights
    """
    i, weights, data_loader, venues, time_slots, day, total = args
    w_travel, w_crowd, w_venues = weights
    return run_model_with_weights(
        data_loader=data_loader,
        venues=venues,
        time_slots=time_slots,
        day=day,
        w_travel=w_travel,
        w_crowd=w_crowd,
        w_venues=w_venues,
        i=i,
        total=total
    )


def run_pareto_analysis(
    day: str = "Tuesday",
    n_weight_points: int = 4,
    output_dir: Optional[str] = None,
    max_workers: Optional[int] = None
) -> Tuple[List[Dict], List[Dict]]:
    """Run a full Pareto analysis for the tour optimization problem.
    
    Args:
        day: Day of the week for the tour
        n_weight_points: Number of points for each weight 
                         (generates n_weight_points^3 combinations)
        output_dir: Directory to save output files (optional)
        max_workers: Maximum number of parallel workers (default: None, which 
                     uses the number of processors on the machine)
    
    Returns:
        Tuple of (all_solutions, pareto_solutions)
    """
    # Set up paths
    data_dir = Path(__file__).parent.parent.parent / "data"
    
    # Initialize data loader
    data_loader = DataLoader(data_dir)
    
    # Generate time slots
    time_slots = generate_time_slots()
    
    # Load venue data to get list of venues
    venue_data, dwell_times, _, _, _ = data_loader.load_all(time_slots)
    
    # Get list of venues
    venues = list(dwell_times.keys())
    
    # Generate weight combinations
    weight_combinations = generate_weight_combinations(n_weight_points)
    
    print(
        f"Running {len(weight_combinations)} weight combinations "
        f"with up to {max_workers} parallel workers"
    )
    
    # Run model with each weight combination in parallel
    all_solutions = []
    
    # Use ProcessPoolExecutor for CPU-bound tasks
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=max_workers
    ) as executor:
        # Prepare arguments for each worker
        worker_args = [
            (i, weights, data_loader, venues, time_slots, day, 
             len(weight_combinations))
            for i, weights in enumerate(weight_combinations)
        ]
        
        # Submit all tasks and collect results
        for solution in executor.map(worker_run_model, worker_args):
            if solution:
                all_solutions.append(solution)
    
    # Identify Pareto-optimal solutions
    pareto_solutions = identify_pareto_optimal_solutions(all_solutions)
    
    print(f"Found {len(all_solutions)} valid solutions")
    print(f"Identified {len(pareto_solutions)} Pareto-optimal solutions")
    
    # Visualize Pareto front
    if output_dir:
        output_path = Path(output_dir) / "pareto_front.png"
        visualize_pareto_front(all_solutions, pareto_solutions, str(output_path))
    else:
        visualize_pareto_front(all_solutions, pareto_solutions)
    
    # Save solutions to CSV
    if output_dir:
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(exist_ok=True)
        
        # Create DataFrame for all solutions
        solution_data = []
        for sol in all_solutions:
            metrics = sol["metrics"]
            weights = sol["weights"]
            solution_data.append({
                "travel_time": metrics["total_travel_time_minutes"],
                "crowd_level": metrics["average_crowd_level"],
                "venues_visited": metrics["total_venues"],
                "w_travel": weights["w_travel"],
                "w_crowd": weights["w_crowd"],
                "w_venues": weights["w_venues"],
                "is_pareto_optimal": sol in pareto_solutions
            })
        
        df = pd.DataFrame(solution_data)
        df.to_csv(output_dir_path / "pareto_solutions.csv", index=False)
    
    return all_solutions, pareto_solutions


if __name__ == "__main__":
    # Run Pareto analysis with parallel execution
    # Use 4 workers (or None to use all available cores)
    run_pareto_analysis(output_dir="pareto_results", max_workers=4) 