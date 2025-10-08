import json
import os
from pulp import value

def save_solution_to_json(n, results, output_dir="../res/MIP", silent=False):
    """
    Save all solver results to a JSON file in the specified format.
    
    Args:
        n: Number of teams
        results: Dictionary with solver results
        output_dir: Directory to save the JSON file
        silent: if True, don't print the save message
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{n}.json")
    
    # Load the existing results if the file exists
    existing_results = {}
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                existing_results = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing_results = {}
    
    # Update with new results
    existing_results.update(results)
    
    with open(filename, 'w') as f:
        json.dump(existing_results, f, indent=2)
    
    if not silent:
        print(f"Results saved to {filename}")

def extract_schedule_from_solution(n, opp, home, period):
    """
    Extract the tournament schedule from the solved model variables.
    
    Args:
        n: Number of teams
        opp: Opponent decision variables
        home: Home decision variables  
        period: Period decision variables
    
    Returns:
        (n/2) × (n-1) matrix: periods × weeks, where each entry is [home_team, away_team]
    """
    W = n - 1
    P = n // 2
    Weeks = range(W)
    Periods = range(P)
    
    # Initialize the solution matrix: periods × weeks
    schedule = [[None for _ in range(W)] for _ in range(P)]
    
    for w in Weeks:
        pairs = set()
        
        for t1 in range(n):
            for t2 in range(n):
                if t1 != t2 and value(opp[w][t1][t2]) > 0.5 and (t2, t1) not in pairs:
                    # Find the period for this match
                    p = next((p for p in Periods if value(period[w][t1][p]) > 0.5), None)
                    if p is not None:
                        if value(home[w][t1]) > 0.5:
                            # t1 is home, t2 is away
                            schedule[p][w]=[t1+1,t2+1]  # Convert to 1-indexed
                        else:
                            # t2 is home, t1 is away  
                            schedule[p][w] = [t2+1,t1+ 1]  # Convert to 1-indexed
                        pairs.add((t1, t2))
    
    return schedule

def calculate_breaks(n, home):
    """ 
    Calculate the total number of breaks in the schedule.
    
    Args:
        n: Number of teams
        home: Home decision variables
    
    Returns:
        Total number of breaks
    """
    W = n - 1
    total_breaks = 0
    
    for t in range(n):
        breaks = 0
        last = None
        for w in range(W):
            cur = value(home[w][t]) > 0.5
            if last is not None and last == cur:
                breaks += 1
            last = cur
        total_breaks += breaks
    
    return total_breaks

def get_solver_display_name(solver_choice, is_optimization=False, has_symmetry_breaking=False):
    """
    Get the display name for the solver based on the configuration.
    
    Args:
        solver_choice: The solver name
        is_optimization: Whether this is optimization or satisfiability
        has_symmetry_breaking: Whether symmetry breaking is enabled
    
    Returns:
        String representing the solver configuration
    """
    # Map solver names to short names
    solver_map = {
        "PULP_CBC_CMD": "CBC",
        "SCIP_PY": "SCIP", 
        "HiGHS": "HiGHS"
    }
    
    solver_short=solver_map.get(solver_choice,solver_choice)
    
    if is_optimization:
        base_name=f"mip_opt_{solver_short}"
    else:
        base_name=f"mip_satisf_{solver_short}"
    
    if has_symmetry_breaking:
        base_name+="_SB"
    
    return base_name
