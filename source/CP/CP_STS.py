#!/usr/bin/env python3
import argparse
import time
import sys
import os
from cp_docker_utils import save_solution_to_json, run_minizinc_model_direct

MODEL_MAPPING = {
    # Chuffed models
    1: ("CP/Chuffed/satisfiability_ch_base.mzn", "Chuffed - Satisfiability Base"),
    2: ("CP/Chuffed/satisfiability_ch_FF.mzn", "Chuffed - Satisfiability First-Fail"),
    3: ("CP/Chuffed/satisfiability_ch_Rand.mzn", "Chuffed - Satisfiability Random"),
    4: ("CP/Chuffed/satisfiability_ch_SB_base.mzn", "Chuffed - Satisfiability Symmetry Breaking Base"),
    5: ("CP/Chuffed/satisfiability_ch_SB_FF.mzn", "Chuffed - Satisfiability Symmetry Breaking First-Fail"),
    6: ("CP/Chuffed/satisfiability_ch_SB_Rand.mzn", "Chuffed - Satisfiability Symmetry Breaking Random"),
    7: ("CP/Chuffed/optimiz_ch_FF.mzn", "Chuffed - Optimization First-Fail"),
    8: ("CP/Chuffed/optimiz_ch_FF_Luby.mzn", "Chuffed - Optimization First-Fail Luby"),
    9: ("CP/Chuffed/optimiz_ch_Rand.mzn", "Chuffed - Optimization Random"),
    10: ("CP/Chuffed/optimiz_ch_Rand_Luby.mzn", "Chuffed - Optimization Random Luby"),
    
    # Gecode models
    11: ("CP/GeoCode/satisfiability_base.mzn", "Gecode - Satisfiability Base"),
    12: ("CP/GeoCode/satisfiability_FF.mzn", "Gecode - Satisfiability First-Fail"),
    13: ("CP/GeoCode/satisfiability_DWD_Min.mzn", "Gecode - Satisfiability Domain/Weight/Degree Min"),
    14: ("CP/GeoCode/satisfiability_DWD_rand.mzn", "Gecode - Satisfiability Domain/Weight/Degree Random"),
    15: ("CP/GeoCode/satisfiability_SB_base.mzn", "Gecode - Satisfiability Symmetry Breaking Base"),
    16: ("CP/GeoCode/satisfiability_SB_FF.mzn", "Gecode - Satisfiability Symmetry Breaking First-Fail"),
    17: ("CP/GeoCode/satisfiability_SB_DWD_Min.mzn", "Gecode - Satisfiability Symmetry Breaking DWD Min"),
    18: ("CP/GeoCode/satisfiability_SB_DWD_rand.mzn", "Gecode - Satisfiability Symmetry Breaking DWD Random"),
    19: ("CP/GeoCode/optimiz_impl_FF.mzn", "Gecode - Optimization Implied First-Fail"),
    20: ("CP/GeoCode/optimiz_impl_DWD.mzn", "Gecode - Optimization Implied Domain/Weight/Degree"),
    21: ("CP/GeoCode/optimiz_impl_DWD_NoSB.mzn", "Gecode - Optimization Implied DWD No Symmetry Breaking"),
    22: ("CP/GeoCode/optimiz_impl_DWD_Luby.mzn", "Gecode - Optimization Implied DWD Luby"),
    23: ("CP/GeoCode/optimiz_impl_DWD_Luby_LNS.mzn", "Gecode - Optimization Implied DWD Luby LNS"),
    24: ("CP/GeoCode/optimiz_impl_base_FF_noSB.mzn", "Gecode - Optimization Implied Base First-Fail No SB"),
    25: ("CP/GeoCode/optimiz_impl_base_FF_Luby.mzn", "Gecode - Optimization Implied Base First-Fail Luby"),
    26: ("CP/GeoCode/optimiz_impl_base_FF_Luby_LNS.mzn", "Gecode - Optimization Implied Base First-Fail Luby LNS"),
    
    # OR-Tools models
    27: ("CP/OR_tools/satisfiability_OR_base.mzn", "OR-Tools - Satisfiability Base"),
    28: ("CP/OR_tools/satisfiability_OR_FF.mzn", "OR-Tools - Satisfiability First-Fail"),
    29: ("CP/OR_tools/satisfiability_OR_DWD.mzn", "OR-Tools - Satisfiability Domain/Weight/Degree"),
    30: ("CP/OR_tools/satisfiability_OR_SB_base.mzn", "OR-Tools - Satisfiability Symmetry Breaking Base"),
    31: ("CP/OR_tools/satisfiability_OR_SB_FF.mzn", "OR-Tools - Satisfiability Symmetry Breaking First-Fail"),
    32: ("CP/OR_tools/satisfiability_OR_SB_DWD.mzn", "OR-Tools - Satisfiability Symmetry Breaking DWD"),
    33: ("CP/OR_tools/optimiz_OR_FF.mzn", "OR-Tools - Optimization First-Fail"),
    34: ("CP/OR_tools/optimiz_OR_DWD.mzn", "OR-Tools - Optimization Domain/Weight/Degree"),
}


def solve_single_configuration(n, model_number, time_limit=300):
    """
    Solve with a single model configuration using model number.
    
    Args:
        n: Number of teams
        model_number: Number corresponding to a specific model (1-34)
        time_limit: Time limit in seconds
    """
    if model_number not in MODEL_MAPPING:
        print(f"Model number {model_number} not found.")
        print("Use --models to see available models.")
        return
    
    model_file, description = MODEL_MAPPING[model_number]
    
    # Automatically detect if it's an optimization problem
    is_optimization = 'optim' in model_file.lower()
    
    # Extract solver from the path
    solver_choice = extract_solver_from_path(model_file)
    
    # Create solver name for result saving
    model_name = os.path.basename(model_file)[:-4]  # Remove .mzn extension
    solver_name = get_solver_display_name_simple(model_name, is_optimization, solver_choice)
    
    result = solve_instance_direct(n, model_file, solver_choice, is_optimization, time_limit)
    
    # Save result
    results = {solver_name: result}
    save_solution_to_json(n, results)
    
    # Print status message
    if result["optimal"] or result["sol"]:
        print("Everything worked fine.")
        print(f"Model: {solver_name}")
        if is_optimization and result["obj"] is not None and result["obj"] != "None":
            print(f"Objective: {result['obj']}, Optimal: {result['optimal']}")
    else:
        print("No solution found.")
        print(f"Model: {solver_name}")


def list_available_models():
    """
    List all available models with their numbers and descriptions.
    """
    print("Available CP models:")
    print("=" * 80)
    
    current_category = ""
    for model_num in sorted(MODEL_MAPPING.keys()):
        model_file, description = MODEL_MAPPING[model_num]
        
        if "Chuffed" in description and current_category != "Chuffed":
            current_category = "Chuffed"
            print(f"\n{current_category} Models:")
            print("-" * 40)
        elif "Gecode" in description and current_category != "Gecode":
            current_category = "Gecode"
            print(f"\n{current_category} Models:")
            print("-" * 40)
        elif "OR-Tools" in description and current_category != "OR-Tools":
            current_category = "OR-Tools"
            print(f"\n{current_category} Models:")
            print("-" * 40)
            
        print(f"{model_num:2d}: {description}")

def extract_solver_from_path(model_file):
    """
    Extract solver name from the model file path.
    """
    if "Chuffed" in model_file:
        return "chuffed"
    elif "GeoCode" in model_file:
        return "gecode"
    elif "OR_tools" in model_file:
        return "com.google.ortools.sat"
    return "gecode"


def get_solver_display_name_simple(model_name, is_optimization=False, solver_choice=None):
    """
    Get a display name with solver name followed by the file name.
    """
    if solver_choice:
        solver_name = solver_choice.lower()
    else:
        # Fallback: try to extract from model path
        if 'chuffed' in model_name.lower() or 'ch_' in model_name.lower():
            solver_name = 'chuffed'
        elif 'gecode' in model_name.lower() or 'impl_' in model_name.lower():
            solver_name = 'gecode'
        elif 'or_tools' in model_name.lower() or '_OR_' in model_name:
            solver_name = 'or_tools'
        else:
            solver_name = 'cp'
    
    return f"{solver_name}_{model_name}"


def solve_instance_direct(n, model_file, solver_choice, is_optimization=False, time_limit=300):
    """
    Solve using a direct model file path.
    """
    try:
        result = run_minizinc_model_direct(n, model_file, solver_choice, is_optimization, time_limit)
        
        # Safeguard: never record times longer than timeout + buffer
        if result["time"] > time_limit + 5:
            result["time"] = time_limit
            result["optimal"] = False
        
        return result
        
    except Exception as e:
        print(f"Error solving with {model_file}: {e}")
        return {
            "time": time_limit,
            "optimal":False,
            "obj":None,
            "sol":None
        }


def solve_all_instances():
    """
    Solve all instances with all available models.
    """
    instances = [2,4,6,8,10,12,14]
    
    for i, n in enumerate(instances):
        success_count = 0
        models_run = []
        all_results = {}  # Collect all results for this instance
        
        for model_num in sorted(MODEL_MAPPING.keys()):
            model_file, description = MODEL_MAPPING[model_num]
            models_run.append(model_num)
            
            # Automatically detect if it's an optimization problem
            is_optimization = 'optim' in model_file.lower()
            
            # Extract solver from the path
            solver_choice = extract_solver_from_path(model_file)
            
            # Create solver name for result saving
            model_name = os.path.basename(model_file)[:-4]  # Remove .mzn extension
            solver_name = get_solver_display_name_simple(model_name, is_optimization, solver_choice)
            
            result = solve_instance_direct(
                n, model_file, solver_choice, is_optimization
            )
            
            # Store result in memory (don't save to file yet)
            all_results[solver_name] = result
            
            if result["optimal"] or result["sol"]:
                success_count += 1
        
        # Save ALL results for this instance at once (at the end)
        save_solution_to_json(n, all_results, silent=True)
        
        # Print completion message when instance is done
        print(f"Instance N={n} done")
        print("="*80)
        sys.stdout.flush()  # Force output to appear immediately


def main():
    parser = argparse.ArgumentParser(
        description="CP solver for Sports Tournament Scheduling Problem",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Each model number corresponds to a specific MiniZinc file and solver combination.
Use --models to see the complete list of available models (1-34).
Optimization/Satisfiability is automatically detected from the model file.
        """
    )
    
    parser.add_argument('-n',type=int,help='Number of teams (must be even)')
    parser.add_argument('--model',type=int,
                       help='Model number (1-34). Use --models to see available models')
    parser.add_argument('--models',action='store_true',
                       help='List all available models with their numbers')
    parser.add_argument('-a',action='store_true',
                       help='Solve all instances with all available models')
    parser.add_argument('-t', '--time-limit',type=int,default=300,
                       help='Time limit in seconds (default: 300)')
    
    args = parser.parse_args()
    
    if args.models:
        list_available_models()
    elif args.a:
        solve_all_instances()
    elif args.n is not None and args.model is not None:
        if args.n % 2!=0:
            print("Error: Number of teams must be even")
            sys.exit(1)
        
        solve_single_configuration(
            args.n,
            args.model,
            args.time_limit
        )
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
