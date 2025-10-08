from itertools import combinations
from z3 import *
import time
import math
import argparse
import json
import os
import sys

# utils
# naive pairwise encoding
def at_least_one_np(bool_vars):
    return Or(bool_vars)

def at_most_one_np(bool_vars, name = ""):
    return And([Not(And(pair[0], pair[1])) for pair in combinations(bool_vars, 2)])

def exactly_one_np(bool_vars, name = ""):
    return And(at_least_one_np(bool_vars), at_most_one_np(bool_vars, name))

#Heule encoding
def at_least_one_he(bool_vars):
    return at_least_one_np(bool_vars)

def at_most_one_he(bool_vars, name):
    if len(bool_vars) <= 4:
        return And(at_most_one_np(bool_vars))
    y = Bool(f"y_{name}")
    return And(And(at_most_one_np(bool_vars[:3] + [y])), And(at_most_one_he(bool_vars[3:] + [Not(y)], name+"_")))

def exactly_one_he(bool_vars, name):
    return And(at_most_one_he(bool_vars, name), at_least_one_he(bool_vars))

class Sat_Model:
    def __init__(self,n, at_least_one, at_most_one, exactly_one):
        #we initialize the parameters
        self.n=n
        self.W=n-1
        self.P=n//2
        self.Teams=range(n)
        self.Weeks=range(self.W)
        self.Periods=range(self.P)
        self.at_least_one = at_least_one
        self.at_most_one = at_most_one
        self.exactly_one = exactly_one
        # match[w][i][j] =is true if the team i plays against the team j in the  week  w
        self.matches =[[[Bool(f"match_{w}_{i}_{j}") for j in  self.Teams] for i in self.Teams ] for w in self.Weeks]
    
        # home[w][i] =is true if the team i plays at home in the week w
        self.homes =[[Bool(f"home_{w}_{i}") for i in self.Teams ] for w in self.Weeks ]
    
        # period[w][i][p] =true if the team i plays in period p in the week w
        self.periods =[[[Bool(f"period_{w}_{i}_{p}") for p in self.Periods] for i in self.Teams ] for w in self.Weeks]

        self.s=Solver()
        self.model_satisfiable_constraints()
    
    def model_satisfiable_constraints(self):

        # we define the constraints
        # every team plays once per week
        for w in self.Weeks:
            for t in self.Teams:
                opponents=[]
                for opp in self.Teams:
                    if opp!=t:
                        if t<opp:
                            opponents.append( self.matches[w][t][opp])
                        else:
                            opponents.append( self.matches[w][opp][t])
                self.s.add(self.exactly_one(opponents, name=f"team_{t}_week_{w}"))

        #Every team plays against each other once in the entire tournament (SRR)
        for i in self.Teams:
            for j in self.Teams:
                if i <  j:
                    meetings =[self.matches[w][i][j] for w  in self.Weeks]
                    self.s.add(self.exactly_one(meetings, name=f"match_{i}_{j}"))

        #Every team plays in exactly one period a week
        for w in  self.Weeks:
            for t in self.Teams:
                self.s.add(self.exactly_one([self.periods[w][t][p] for   p in self.Periods], name=f"period_{w}_{t}"))

        #Every period contains a match ( 2 teams)
        for w in self.Weeks:
            for p in self.Periods:
                count_teams =Sum([If(self.periods[w][t][p],1,0) for t in self.Teams])
                self.s.add(count_teams ==2)
        
        # if team A plays team B , they share the same period
        for w in self.Weeks:
            for i in self.Teams:
                for j in self.Teams:
                    if i < j:
                        self.s.add(Implies(self.matches[w][i][j], 
                                        And([self.periods[w][i][p]==self.periods[w][j][p] for p in self.Periods])))
        
        # one team is Home and one away in the same match
        for w in self.Weeks:
            for i in self.Teams:
                for j in self.Teams:
                    if i<j:
                        self.s.add(Implies(self.matches[w][i][j], 
                                        self.homes[w][i]!=self.homes[w][j])) #just ONE at home
        
        # each team must appear max 2 times in the same period along the tournament
        for t in self.Teams:
            for p in self.Periods:
                count_teams_period =Sum([If(self.periods[w][t][p],1,0) for w in self.Weeks])
                self.s.add(count_teams_period<=2)
                
        
    def add_symmetry(self):
        #week permutation sb constraint
        for w in range(1, self.W):
            prev_opp =Sum([If(self.matches[w-1][0][opp],opp,0) for opp in range(1,self.n)])
            curr_opp =Sum([If(self.matches[w][0][opp],opp,0) for opp in range(1,self.n)])
            self.s.add(curr_opp>prev_opp)

    def solve(self,timeout=300,symmetry=False):
        """
        Function to solve the problem with/out SB and 5 min timeout"""
        if symmetry:
            self.add_symmetry()

        # We set the timeout
        self.s.set("timeout",timeout*1000)

        start_time =time.time()

        if self.s.check() ==sat:
            solve_time =time.time()-start_time
            m =self.s.model()
            
            # we Extract the solution
            schedule ={"weeks": []}
            
            for w in self.Weeks:
                week_matches =[]
                for i in self.Teams:
                    for j in self.Teams:
                        if i < j and m.evaluate(self.matches[w][i][j]):
                            # Find period
                            period =0
                            for p in self.Periods:
                                if m.evaluate(self.periods[w][i][p]):
                                    period =p
                                    break
                            
                            # Find home/away
                            home_team =i if m.evaluate(self.homes[w][i]) else j
                            away_team =j if m.evaluate(self.homes[w][i]) else i
                            
                            week_matches.append({
                                "home_team":home_team,
                                "away_team":away_team,
                                "period":period
                            })
                
                schedule["weeks"].append(week_matches)
            
            return {
                "time":solve_time,
                "feasible":True,
                "schedule":schedule
            }
        else:
            solve_time =time.time() - start_time
            return {
                "time": solve_time,
                "feasible": False,
                "schedule": None
            }
        

def model_satisfiable_sat(n,symmetry=False,timeout=300,at_least_one=None, at_most_one=None, exactly_one=None):
    """
    Wrapper function to create the sat model and solve it
    """
    assert n%2==0, "Remeber team n is even"
    
    # Using only 1 core
    set_param("parallel.enable",False)
    set_param("parallel.threads.max",1)
    set_param("sat.threads",1)
    
    try:
        sat_model=Sat_Model(n,at_least_one,at_most_one,exactly_one)
        result=sat_model.solve(timeout=timeout,symmetry=symmetry)
        return result
        
    except Exception as e:
        return {
            "time":timeout,
            "feasible":False,
            "schedule":None
        }
    



def save_solution_to_json(n,results,output_dir="../res/SAT",silent=False):
    """Save SAT results to JSON file, updating existing results"""
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{n}.json")
    
    # Load existing results if the file exists
    existing_results = {}
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                existing_results =json.load(f)
        except (json.JSONDecodeError,IOError):
            existing_results={}
    
    # Process new results
    new_results = {}
    for result_key, result_data in results.items():
        if result_data["feasible"]:
            # Convert schedule to format matching specification
            n_periods = n // 2
            n_weeks = n - 1
            
            # Initialize the solution matrix
            sol = [[None for _ in range(n_weeks)] for _ in range(n_periods)]
            
            for week_idx, week_data in enumerate(result_data["schedule"]["weeks"]):
                for match in week_data:
                    period = match["period"]
                    # Convert 0-indexed to 1-indexed for consistency
                    home_team = match["home_team"] + 1
                    away_team = match["away_team"] + 1
                    sol[period][week_idx] = [home_team, away_team]
            
            new_results[result_key] = {
                "time": round(result_data["time"]),
                "optimal": True,  # SAT problems are satisfiability, so if solved it's "optimal"
                "obj": None,
                "sol": sol
            }
        else:
            # Check if timeout
            solve_time = result_data.get("time", 0)
            if solve_time >= 299:  # Timeout (300s with tolerance)
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

def solve_instance(n, encoding="both", symmetry=False, time_limit=300):
    """Solve SAT instance with specified encoding"""
    results = {}
    
    if encoding in ["both", "np"]:
        result = model_satisfiable_sat(
            n, 
            symmetry=symmetry, 
            timeout=time_limit,
            at_least_one=at_least_one_np,
            at_most_one=at_most_one_np,
            exactly_one=exactly_one_np
        )
        results[f"sat_np{'_sb' if symmetry else ''}"] = result
    
    if encoding in ["both", "heule"]:
        result = model_satisfiable_sat(
            n,
            symmetry=symmetry,
            timeout=time_limit, 
            at_least_one=at_least_one_he,
            at_most_one=at_most_one_he,
            exactly_one=exactly_one_he
        )
        results[f"sat_heule{'_sb' if symmetry else ''}"] = result
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SAT solver for Sports Tournament Scheduling Problem')
    parser.add_argument('-n', '--teams', type=int, help='Number of teams (must be even)')
    parser.add_argument('--encoding', choices=['np', 'heule', 'both'], default='both',
                       help='SAT encoding to use (default: both)')
    parser.add_argument('-s', '--symmetry', action='store_true', 
                       help='Enable symmetry breaking constraints')
    parser.add_argument('-t', '--time-limit', type=int, default=300,
                       help='Time limit in seconds (default: 300)')
    parser.add_argument('-a', '--auto', action='store_true',
                       help='Run all instances with all configurations automatically')
    
    args = parser.parse_args()
    
    if args.auto:
        
        instances = [2,4, 6, 8, 10, 12, 14, 16,18]
        for n in instances:
            if n % 2 != 0:
                continue
            
            success_count = 0
            
            for symmetry in [False, True]:
                for encoding in ['np', 'heule']:
                    try:
                        results = solve_instance(n, encoding, symmetry, args.time_limit)
                        
                        # Save immediately after each configuration (silent mode)
                        save_solution_to_json(n, results, silent=True)
                        
                        # Count successful solutions
                        success_count += sum(1 for result in results.values() if result["feasible"])
                    except Exception as e:
                        print(f"Error solving N={n} with {encoding} encoding (SB={symmetry}): {e}")
            
            # Print save message only once at the end of instance
            print(f"Results saved to ../res/SAT/{n}.json")
            
            # Print overall status for this instance
            total_configs =4
            print(f"Instance N={n} completed. {success_count}/{total_configs} configurations found solutions.")
            print("="*80)
            sys.stdout.flush()  # Force output to appear immediately
    
    elif args.teams:
        if args.teams % 2 != 0:
            print("Error: Number of teams must be even")
            exit(1)
            
        results =solve_instance(args.teams, args.encoding, args.symmetry, args.time_limit)
        
        # Save results  
        save_solution_to_json(args.teams, results)
        
        solutions_found = sum(1 for result in results.values() if result["feasible"])
        if solutions_found >0:
            print("Everything worked fine.")
            
            successful_models =[key for key, result in results.items() if result["feasible"]]
            print(f"Models: {', '.join(successful_models)}")
        else:
            print("No solution found.")
            attempted_models =list(results.keys())
            print(f"Models: {', '.join(attempted_models)}")
    
    else:
        parser.print_help()