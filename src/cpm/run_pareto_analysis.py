#!/usr/bin/env python3
"""Script to run Pareto Optimality Analysis for the Tour Optimization Model.

This script runs a Pareto Optimality Analysis for the TourOptimizer model,
generating multiple solutions with different weight combinations, identifying
Pareto-optimal solutions, and visualizing the Pareto front.

Usage:
    python -m src.cpm.run_pareto_analysis [--day DAY] [--points POINTS] [--output DIR]

Arguments:
    --day DAY        Day of the week for the tour (default: Tuesday)
    --points POINTS  Number of points for each weight (default: 5)
    --output DIR     Directory to save output files (default: pareto_results)
"""

import argparse
from pathlib import Path
from .pareto_analysis import run_pareto_analysis


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Pareto Optimality Analysis for Tour Optimization"
    )
    parser.add_argument(
        "--day",
        type=str,
        default="Tuesday",
        choices=[
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        ],
        help="Day of the week for the tour (default: Tuesday)"
    )
    parser.add_argument(
        "--points",
        type=int,
        default=5,
        help="Number of points for each weight (default: 5)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="pareto_results",
        help="Directory to save output files (default: pareto_results)"
    )
    return parser.parse_args()


def main():
    """Run the Pareto analysis with command line arguments."""
    args = parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    print(
        f"Running Pareto analysis for {args.day} with {args.points} "
        f"points per weight"
    )
    print(f"Output will be saved to {output_dir.absolute()}")
    
    # Run the analysis
    all_solutions, pareto_solutions = run_pareto_analysis(
        day=args.day,
        n_weight_points=args.points,
        output_dir=str(output_dir)
    )
    
    print("\nAnalysis complete!")
    print(f"Generated {len(all_solutions)} solutions")
    print(f"Found {len(pareto_solutions)} Pareto-optimal solutions")
    print(f"Results saved to {output_dir.absolute()}")


if __name__ == "__main__":
    main() 