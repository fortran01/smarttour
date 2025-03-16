#!/usr/bin/env python3
"""Test script for Pareto Optimality Analysis.

This script demonstrates the Pareto Optimality Analysis for the TourOptimizer
model with a small number of weight combinations for quick testing.
"""

from pathlib import Path
from .pareto_analysis import run_pareto_analysis


def main():
    """Run a quick test of the Pareto analysis."""
    print("Running Pareto Optimality Analysis test...")
    
    # Create output directory
    output_dir = Path("pareto_test_results")
    output_dir.mkdir(exist_ok=True)
    
    # Run analysis with a small number of weight points for quick testing
    all_solutions, pareto_solutions = run_pareto_analysis(
        day="Tuesday",
        n_weight_points=3,  # Small number for quick testing
        output_dir=str(output_dir)
    )
    
    print("\nTest complete!")
    print(f"Generated {len(all_solutions)} solutions")
    print(f"Found {len(pareto_solutions)} Pareto-optimal solutions")
    print(f"Results saved to {output_dir.absolute()}")
    
    # Print details of Pareto-optimal solutions
    print("\nPareto-optimal solutions:")
    for i, sol in enumerate(pareto_solutions):
        metrics = sol["metrics"]
        weights = sol["weights"]
        print(f"\nSolution {i+1}:")
        print(f"  Travel time: {metrics['total_travel_time_minutes']} minutes")
        print(f"  Crowd level: {metrics['average_crowd_level']:.2f}")
        print(f"  Venues visited: {metrics['total_venues']}")
        print(
            f"  Weights: travel={weights['w_travel']:.2f}, "
            f"crowd={weights['w_crowd']:.2f}, venues={weights['w_venues']:.2f}"
        )
        print(f"  Venues: {', '.join(sol['selected_venues'])}")


if __name__ == "__main__":
    main() 