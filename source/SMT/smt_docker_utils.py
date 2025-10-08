#!/usr/bin/env python3
import json
import os

def save_solution_to_json(n,results,output_dir="../res/SMT",silent=False):
    """Save SMT results to JSON file, updating existing results"""
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{n}.json")
    
    # Load existing results if the file exists
    existing_results = {}
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                existing_results = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing_results = {}
    
    new_results = {}
    for result_key, result_data in results.items():
        # check if we have a solution
        if "smt_opt" in result_key:
            # Optimization version
            has_solution = result_data.get("schedule") is not None and result_data.get("obj") is not None
            if has_solution:
                optimal_obj = n - 2  # Theoretical minimum breaks
                is_optimal = result_data["optimal"] and (result_data["obj"] == optimal_obj)
                
                new_results[result_key] = {
                    "time": round(result_data["time"]),
                    "optimal": is_optimal,
                    "obj": result_data["obj"],
                    "sol": convert_schedule_to_periods(n, result_data["schedule"])
                }
            else:
                # Check if it's timeout, unfeasible, or error
                solve_time = result_data.get("time", 0)
                if solve_time >= 299:  # Timeout (300s with tolerance)
                    new_results[result_key] = {
                        "time": 300,
                        "optimal": False,
                        "obj": None, 
                        "sol": []
                    }
                elif solve_time < 1:  # Unfeasible (solved quickly)
                    new_results[result_key] = {
                        "time": 0,
                        "optimal": True,
                        "obj": None, 
                        "sol": []
                    }
                else:  # Other error
                    new_results[result_key] = {
                        "time": round(solve_time),
                        "optimal": False,
                        "obj": None, 
                        "sol": []
                    }
        else:
            # Satisfiability version
            if result_data.get("feasible", False):
                new_results[result_key] = {
                    "time": round(result_data["time"]),
                    "optimal": True,
                    "obj": None,  # Use None for satisfiability
                    "sol": convert_schedule_to_periods(n, result_data["schedule"])
                }
            else:
                # Check if timeout
                solve_time = result_data.get("time", 0)
                if solve_time >= 299:  # Timeout
                    new_results[result_key] = {
                        "time": 300,
                        "optimal": False,
                        "obj": None, 
                        "sol": []
                    }
                else:
                    # UNSAT case - solver proved there's no solution, which is optimal
                    new_results[result_key] = {
                        "time": round(solve_time),
                        "optimal": True,  # UNSAT is optimal - solver proved no solution exists
                        "obj": None, 
                        "sol": []
                    }
    
    # Update existing results with new results
    existing_results.update(new_results)
    
    with open(filename, 'w') as f:
        json.dump(existing_results, f, indent=2)
    
    if not silent:
        print(f"Results saved to {filename}")

def convert_schedule_to_periods(n, schedule):
    """Convert week-based schedule to period-based format for consistency"""
    P = n // 2  # Number of periods
    
    periods = [[] for _ in range(P)]
    
    for week_idx, week_data in enumerate(schedule["weeks"]):
        for match in week_data:
            # Convert 0-indexed to 1-indexed for consistency with other solvers
            home_team = match["home_team"] + 1
            away_team = match["away_team"] + 1
            period = match["period"]  
            
            periods[period].append([home_team, away_team])
    
    return periods

def get_model_display_name(is_optimization, has_symmetry_breaking):
    """Generate display name for SMT model configuration"""
    model_type = "opt" if is_optimization else "satisf"
    sb_suffix = "_sb" if has_symmetry_breaking else ""
    return f"smt_{model_type}{sb_suffix}"
