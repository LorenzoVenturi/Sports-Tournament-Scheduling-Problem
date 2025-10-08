#!/usr/bin/env python3
import argparse
import time
import sys
import os
from pulp import LpStatus

# Import our model implementations
from MILP_Optimization import optimization_milp_model
from MILP_Optimization_SB import optimization_milp_model as optimization_milp_model_sb
from MILP_Satisfiability import satisfiability_milp_model  
from MILP_Satisfiability_SB import satisfiability_milp_model as satisfiability_milp_model_sb
from mip_docker_utils import save_solution_to_json, extract_schedule_from_solution, calculate_breaks, get_solver_display_name

def solve_instance(n, solver_choice, is_optimization=False, has_symmetry_breaking=False, time_limit=300):
    """
    Solve a single instance with the specified configuration.
    
    Args:
        n: Number of teams
        solver_choice: Solver to use
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
            if has_symmetry_breaking:
                model, opp, home, period, solver = optimization_milp_model_sb(n, solver_choice)
            else:
                model, opp, home, period, solver = optimization_milp_model(n, solver_choice)
        else:
            if has_symmetry_breaking:
                model, opp, home, period, solver = satisfiability_milp_model_sb(n, solver_choice)
            else:
                model, opp, home, period, solver = satisfiability_milp_model(n, solver_choice)
        
        # Update time limit
        solver.timeLimit=time_limit
        
        # Solve the model
        model.solve(solver)
        solve_time = time.time()-start_time
        
        # Extract results (regardless of timeout - solver may have found intermediate solutions)
        status = LpStatus[model.status]
        has_solution = status in ["Optimal"] or (status in ["Not Solved", "Undefined"] and 
                                                any(v.varValue is not None for v in model.variables()))
        
        if has_solution:
            schedule =extract_schedule_from_solution(n, opp, home, period)
            
            # Validate that we have a complete solution 
            is_complete_solution = all(
                all(match is not None for match in week) 
                for week in schedule
            )
            
            if not is_complete_solution:
                # Incomplete solution
                result = {
                    "time": min(round(solve_time), time_limit),
                    "optimal": False,
                    "obj": None,
                    "sol":[]
                }
            else:
                # Complete solution found
                if is_optimization:
                    total_breaks = calculate_breaks(n, home)
                    optimal_obj = n - 2  # Theoretical minimum breaks
                    # Only mark as optimal if solver says optimal AND we have optimal objective
                    is_optimal = (status == "Optimal") and (total_breaks == optimal_obj)
                    
                    result = {
                        "time": min(round(solve_time), time_limit),
                        "optimal": is_optimal,
                        "obj": total_breaks,
                        "sol": schedule
                    }
                else:
                    # For satisfiability problems
                    result = {
                        "time": min(round(solve_time), time_limit),
                        "optimal": (status == "Optimal"),  # Only optimal if solver says so
                        "obj": None,
                        "sol": schedule
                    }
        else:
            # No solution found - check if it's unfeasible or timeout
            if solve_time < 1:  # Unfeasible (solved quickly)
                # For both optimization and satisfiability, UNSAT is an optimal result
                result = {
                    "time": round(solve_time),
                    "optimal": True,
                    "obj": None,
                    "sol": []
                }
            else:
                # Timeout or other error case - no solution found
                result = {
                    "time": min(round(solve_time), time_limit),
                    "optimal": False,
                    "obj": None,
                    "sol": []
                }
        
        return result
        
    except Exception as e:
        print(f"Error solving with {solver_choice}: {e}")
        solve_time = time.time() - start_time
        return {
            "time": round(solve_time),
            "optimal": False,
            "obj": None,
            "sol": []
        }

def solve_single_solver(n, solver_index, is_optimization=False, has_symmetry_breaking=False, time_limit=300):
    """
    Solve with a single solver based on the index.
    
    Args:
        n: Number of teams
        solver_index: Index of the solver (1: CBC, 2: SCIP, 3: HiGHS)
        is_optimization: Whether to solve optimization problem
        has_symmetry_breaking: Whether to use symmetry breaking
        time_limit: Time limit in seconds
    """
    solvers = ["PULP_CBC_CMD", "SCIP_PY", "HiGHS"]
    
    if solver_index < 1 or solver_index > len(solvers):
        print(f"Invalid solver index {solver_index}. Must be 1-{len(solvers)}")
        return
    
    solver_choice = solvers[solver_index - 1]  # Convert 1-based to 0-based indexing
    solver_name = get_solver_display_name(solver_choice, is_optimization, has_symmetry_breaking)
    
    result = solve_instance(n, solver_choice, is_optimization, has_symmetry_breaking, time_limit)
    
    # Save result
    results = {solver_name: result}
    save_solution_to_json(n, results)
    
    # Print status message like CP
    if result["optimal"] or result["sol"]:
        print("Everything worked fine.")
        print(f"Model: {solver_name}")
        if is_optimization and result["obj"] is not None and result["obj"] != "None":
            print(f"Objective: {result['obj']}, Optimal: {result['optimal']}")
    else:
        print("No solution found.")
        print(f"Model: {solver_name}")

def solve_all_instances():
    """
    Solve all instances (N=4,6,8,10) with all solver configurations.
    """
    instances = [2,4, 6, 8, 10]
    solvers = ["PULP_CBC_CMD", "SCIP_PY", "HiGHS"]
    configurations = [
        (False, False),  # satisfiability, no SB
        (False, True),   # satisfiability, with SB  
        (True, False),   # optimization, no SB
        (True, True),    # optimization, with SB
    ]
    
    for n in instances:
        success_count = 0
        
        for solver_choice in solvers:
            for is_optimization, has_symmetry_breaking in configurations:
                solver_name = get_solver_display_name(solver_choice, is_optimization, has_symmetry_breaking)
                
                result = solve_instance(n, solver_choice, is_optimization, has_symmetry_breaking)
                
                single_result = {solver_name: result}
                save_solution_to_json(n, single_result, silent=True)
                
                if result["optimal"] or result["sol"]:
                    success_count += 1
        
        # We print save message only once at the end of instance
        print(f"Results saved to ../res/MIP/{n}.json")
        
        # Print overall status for this instance
        total_configs = len(solvers) * len(configurations)
        print(f"Instance N={n} completed. {success_count}/{total_configs} configurations found solutions.")
        print("="*80)
        sys.stdout.flush()  # Force output to appear immediately

def main():
    parser = argparse.ArgumentParser(
        description="MIP solver for Sports Tournament Scheduling Problem",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mip_model.py -n 6 -solver 1           # Solve N=6 with CBC (satisfiability)
  python mip_model.py -n 8 -solver 2 -o        # Solve N=8 with SCIP (optimization)  
  python mip_model.py -n 6 -solver 3 -o -sb    # Solve N=6 with HiGHS (optimization + symmetry breaking)
  python mip_model.py -a                        # Solve all instances with all configurations

Available solvers:
  1: CBC (PULP_CBC_CMD)
  2: SCIP (SCIP_PY) 
  3: HiGHS (HiGHS)
        """
    )
    
    parser.add_argument('-n', '--teams', type=int, help='Number of teams (must be even)')
    parser.add_argument('-solver', '--solver', type=int, help='Solver choice (1: CBC, 2: SCIP, 3: HiGHS)')
    parser.add_argument('-a', '--all', action='store_true', 
                       help='Solve all instances with all solver configurations')
    parser.add_argument('-o', '--optimization', action='store_true',
                       help='Solve optimization problem (minimize breaks)')
    parser.add_argument('-sb', '--symmetry-breaking', action='store_true',
                       help='Use symmetry breaking constraints')
    parser.add_argument('-t', '--time-limit', type=int, default=300,
                       help='Time limit in seconds (default: 300)')
    
    args = parser.parse_args()
    
    if args.all:
        solve_all_instances()
    elif args.teams is not None and args.solver is not None:
        if args.teams % 2 != 0:
            print("Error: Number of teams must be even")
            sys.exit(1)
        
        solve_single_solver(
            args.teams, 
            args.solver,
            args.optimization,
            args.symmetry_breaking,
            args.time_limit
        )
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
