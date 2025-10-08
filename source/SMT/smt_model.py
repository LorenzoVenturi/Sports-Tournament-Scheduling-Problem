#!/usr/bin/env python3

import argparse
import time
import sys
import os

# Import our model implementations
from STS_SMT_opt import model_optimized
from STS_SMT_satisf import model_satisfiable
from smt_docker_utils import save_solution_to_json, get_model_display_name

def solve_instance(n, is_optimization=False, has_symmetry_breaking=False, time_limit=300):
    """
    Solve a single instance with the specified configuration.
    
    Args:
        n: Number of teams
        is_optimization: Whether to solve optimization or satisfiability problem
        has_symmetry_breaking: Whether to use symmetry breaking constraints
        time_limit: Time limit in seconds
    
    Returns:
        Dictionary with solution results
    """
    start_time = time.time()
    
    try:
        # Select the appropriate model
        if is_optimization:
            result = model_optimized(n,symmetry=has_symmetry_breaking, timeout=time_limit)
        else:
            result = model_satisfiable(n, symmetry=has_symmetry_breaking,timeout=time_limit)
        
        return result
        
    except Exception as e:
        print(f"Error solving SMT model: {e}")
        solve_time =time.time()- start_time
        return {
            "time": round(solve_time),
            "optimal":False,
            "feasible": False,
            "obj":None,
            "schedule": None
        }

def solve_single_model(n,is_optimization=False,has_symmetry_breaking=False,time_limit=300):
    """
    Solve with a single model configuration.
    
    Args:
        n: Number of teams
        is_optimization: Whether to solve optimization problem
        has_symmetry_breaking: Whether to use symmetry breaking
        time_limit: Time limit in seconds
    """
    model_name =get_model_display_name(is_optimization, has_symmetry_breaking)
    
    result= solve_instance(n, is_optimization, has_symmetry_breaking, time_limit)
    
    # Save result
    results= {model_name:result}
    save_solution_to_json(n,results)
    
    if is_optimization:
        has_solution=result.get("schedule") is not None and result.get("obj") is not None
        if has_solution:
            print("Everything worked fine.")
            print(f"Model: {model_name}")
            print(f"Objective: {result['obj']}, Optimal: {result['optimal']}")
        else:
            print("No solution found.")
            print(f"Model: {model_name}")
    else:
        if result["feasible"]:
            print("Everything worked fine.")
            print(f"Model: {model_name}")
        else:
            print("No solution found.")
            print(f"Model: {model_name}")

def solve_all_instances():
    """
    Solve all instances (N=4,6,8,10,12,14,16) with all model configurations.
    """
    instances = [2,4, 6, 8, 10, 12, 14, 16]
    configurations = [
        (False,False),  # satisfiability, no SB
        (False,True),   # satisfiability, with SB  
        (True,False),   # optimization, no SB
        (True,True),    # optimization, with SB
    ]
    
    for n in instances:
        success_count =0
        
        for is_optimization,has_symmetry_breaking in configurations:
            model_name =get_model_display_name(is_optimization,has_symmetry_breaking)
            
            result = solve_instance(n, is_optimization,has_symmetry_breaking)
            
            # Save immediately after each configuration (silent mode)
            single_result={model_name: result}
            save_solution_to_json(n,single_result,silent=True)
            
            # Count successful solutions
            if is_optimization:
                has_solution =result.get("schedule") is not None and result.get("obj") is not None
                if has_solution:
                    success_count+= 1
            else:
                if result["feasible"]:
                    success_count +=1
        
        print(f"Results saved to ../res/SMT/{n}.json")
        
        total_configs = len(configurations)
        print(f"Instance N={n} completed. {success_count}/{total_configs} configurations found solutions.")
        print("="*80)
        sys.stdout.flush()  # Force output to appear immediately

def main():
    parser = argparse.ArgumentParser(
        description="SMT solver for Sports Tournament Scheduling Problem",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python smt_model.py -n 6           # Solve N=6 with satisfiability
  python smt_model.py -n 8 -o        # Solve N=8 with optimization  
  python smt_model.py -n 6 -o -sb    # Solve N=6 with optimization + symmetry breaking
  python smt_model.py -a             # Solve all instances with all configurations

Available models:
  Satisfiability: Find any valid tournament schedule
  Optimization: Find tournament schedule minimizing breaks
        """
    )
    
    parser.add_argument('-n', '--teams', type=int, help='Number of teams (must be even)')
    parser.add_argument('-a', '--all', action='store_true', 
                       help='Solve all instances with all model configurations')
    parser.add_argument('-o', '--optimization', action='store_true',
                       help='Solve optimization problem (minimize breaks)')
    parser.add_argument('-sb', '--symmetry-breaking', action='store_true',
                       help='Use symmetry breaking constraints')
    parser.add_argument('-t', '--time-limit', type=int, default=300,
                       help='Time limit in seconds (default: 300)')
    
    args = parser.parse_args()
    
    if args.all:
        solve_all_instances()
    elif args.teams is not None:
        if args.teams %2 !=0:
            print("Error: Number of teams must be even")
            sys.exit(1)
        
        solve_single_model(
            args.teams,
            args.optimization,
            args.symmetry_breaking,
            args.time_limit
        )
    else:
        parser.print_help()

if __name__ =="__main__":
    main()
