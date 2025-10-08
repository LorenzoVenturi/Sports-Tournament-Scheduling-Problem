import json
import os
import subprocess
import tempfile
import re
import time

def save_solution_to_json(n, results, output_dir="../res/CP", silent=False):
    """
    Save all solver results to a JSON file.
    
    Args:
        n: Number of teams
        results:  a dictionary with solver results
        output_dir: the directory to save the JSON file
        silent: if true,don't print the save message
    """
    os.makedirs(output_dir,exist_ok=True)
    filename = os.path.join(output_dir,f"{n}.json")
    
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

def create_dzn_file(n):
    """
    Create a .dzn data file for the given number of teams.
    
    Args:
        n: Number of teams
    
    Returns:
        Path to the created .dzn file
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.dzn', delete=False) as f:
        f.write(f"n = {n};\n")
        return f.name

def parse_minizinc_output(output, is_optimization=False, n=None):
    """
    Parse the minizinc output.
    
    Args:
        output: raw output from minizinc
        is_optimization: if it is optimization
        n: Number of teams (needed to determine optimal objective)
    
    Returns:
        Dictionary with parsed results
    """
    result = {
        "time": 0.0,
        "optimal": False,
        "obj": None,
        "sol": [],
    }
    
    lines = output.split('\n')
    
    # Check for UNSATISFIABLE
    if "UNSATISFIABLE" in output.upper() or "unsatisfiable" in output.lower():
        result["optimal"] = True  # UNSAT is optimal - solver proved no solution exists
        return result
    
    # Look for period lines with matches (don't rely on header)
    periods = []
    for line in lines:
        if line.strip().startswith("Period"):
            # we extract matches from each column (week)
            matches=re.findall(r'(\d+)\s*v\s*(\d+)',line)
            
            if matches:
                periods.append([[int(match[0]), int(match[1])] for match in matches])
    
    if periods:
        result["sol"]=periods
    
    # If no solution found yet, try alternative formats
    if not result["sol"]:
        schedule_match = re.search(r'schedule\s*=\s*array2d\([^)]+\)\s*\[(.*?)\]', output, re.DOTALL)
        if schedule_match:
            array_content = schedule_match.group(1)
            pass
        
        # We try to parse other MiniZinc output formats
        # we look for variable assignments in the output
        opp_matches = re.findall(r'opp\s*=\s*array2d\([^)]+\)\s*\[(.*?)\]',output,re.DOTALL)
        per_matches = re.findall(r'per\s*=\s*array2d\([^)]+\)\s*\[(.*?)\]',output,re.DOTALL)

        # If both opponent and period arrays are found, we can reconstruct the schedule
        if opp_matches and per_matches:
            # Parse opponent and period arrays to reconstruct the schedule
            # This would require more detailed parsing
            pass

        # Try to find any solution format in the output (even incomplete ones)
        # Look for patterns like "Period 1: team1 v team2, team3 v team4"
        solution_lines = []
        current_period = []
        
        for line in lines:
            line=line.strip()
            if line.startswith("Period") and ":" in line:
                if current_period:
                    solution_lines.append(current_period)
                    current_period=[]
                # Parse matches from the period line
                matches = re.findall(r'(\d+)\s*v\s*(\d+)', line)
                if matches:
                    current_period = [[int(m[0]), int(m[1])] for m in matches]
            elif current_period and re.search(r'\d+\s*v\s*\d+', line):
                # Continue parsing matches on subsequent lines
                matches=re.findall(r'(\d+)\s*v\s*(\d+)', line)
                current_period.extend([[int(m[0]), int(m[1])] for m in matches])
        
        if current_period:
            solution_lines.append(current_period)
            
        if solution_lines:
            result["sol"] = solution_lines

    # Check for optimality or solution found (AFTER parsing solutions)
    has_optimality_marker = "==========" in output or "----------" in output
    
    # We parse objective value if present
    obj_match = re.search(r'obj\s*=\s*(\d+)',output)
    if obj_match:
        result["obj"] = int(obj_match.group(1))
    elif is_optimization:
        # For optimization problems, try to extract from different formats
        obj_match = re.search(r'objective\s*:\s*(\d+)', output, re.IGNORECASE)
        if obj_match:
            result["obj"] = int(obj_match.group(1))
        else:
            breaks_match = re.search(r'Total breaks:\s*(\d+)', output)
            if breaks_match:
                result["obj"] = int(breaks_match.group(1))
            else:
                intermediate_obj = re.findall(r'%?\s*[Oo]bjective:?\s*(\d+)', output)
                if intermediate_obj:
                    result["obj"] = int(intermediate_obj[-1])  # we take the last (best) objective found
    
    # Determine optimality based on MiniZinc markers AND objective value
    if is_optimization and n is not None and result["obj"] is not None:
        optimal_objective = n - 2  # For STS problem, optimal is n-2
        # Only mark as optimal if solver says it's optimal AND objective equals n-2
        result["optimal"] = has_optimality_marker and (result["obj"] == optimal_objective)
    elif has_optimality_marker:
        result["optimal"] = True  # For satisfiability problems, trust the solver
    elif result["sol"]:  # If we found a solution but no optimality marker, it's feasible but not optimal
        result["optimal"] = False
    
    # Parse timing information
    time_match = re.search(r'(\d+(?:\.\d+)?)\s*ms', output)
    if time_match:
        result["time"] = float(time_match.group(1)) / 1000.0
    
    return result

def run_minizinc_model_direct(n, model_file, solver_choice, is_optimization=False, time_limit=300):
    """
    Run a MiniZinc model using a direct file path.
    
    Args:
        n: Number of teams
        model_file: Direct path to the .mzn model file
        solver_choice: Solver to use  
        is_optimization: Whether to solve optimization problem
        time_limit: Time limit in seconds
    
    Returns:
        Dictionary with solution results
    """
    # Map our solver names to MiniZinc solver names
    solver_map = {
        "chuffed": "chuffed",  
        "gecode": "gecode",    
        "or-tools": "com.google.ortools.sat"
    }
    
    minizinc_solver = solver_map.get(solver_choice,solver_choice)
    
    # Create data file
    dzn_file=create_dzn_file(n)
    
    try:
        # Build MiniZinc command
        cmd=[
            "minizinc",
            "--solver", minizinc_solver,
            "--time-limit", str(time_limit * 1000),
            model_file,
            dzn_file
        ]
        
        # Run MiniZinc
        start_time = time.time()
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=time_limit + 5 # the actual time limit is 300 sec
        )
        execution_time = time.time() - start_time
        
        # Parse output
        result = parse_minizinc_output(process.stdout, is_optimization, n)
        
        # If no timing info was parsed, use our measured time
        if result["time"] == 0.0:
            result["time"] = round(execution_time)
        
        return result
        
    except subprocess.TimeoutExpired as e:
        # if subprocess timed out, try to parse any partial output
        partial_output = ""
        if hasattr(e, 'stdout') and e.stdout:
            partial_output = e.stdout
        elif hasattr(e, 'stderr') and e.stderr:
            partial_output = e.stderr
            
        # Try to parse any intermediate solution found before timeout
        result = parse_minizinc_output(partial_output, is_optimization, n) if partial_output else {
            "time": time_limit,
            "optimal": False,
            "obj": None,
            "sol": [], 
        }
        
        # Ensure timeout is recorded correctly
        result["time"] = time_limit
        result["optimal"] = False  # Timeout means not optimal
        
        return result
    except Exception as e:
        print(f"Error running MiniZinc: {e}")
        return {
            "time": 0.0,
            "optimal": False,
            "obj": None,
            "sol": [],
        }
    finally:
        try:
            os.unlink(dzn_file)
        except:
            pass