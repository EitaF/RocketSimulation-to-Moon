#!/usr/bin/env python3
"""
Quick Monte Carlo test with 10 runs to verify the system works
"""

from monte_carlo_validation import MonteCarloValidator

def main():
    print("🧪 Testing Monte Carlo validation with 10 runs...")
    
    # Create validator with small number of runs
    validator = MonteCarloValidator(num_runs=10)
    
    # Run validation
    summary = validator.run_monte_carlo_validation(use_parallel=False, max_workers=1)
    
    # Print results
    success_rate = summary['analysis']['success_rate']
    print(f"\nTest completed: {success_rate:.0%} success rate")
    
    return 0

if __name__ == "__main__":
    exit(main())