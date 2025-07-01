from itertools import combinations
from z3 import *
import time
import math

# utils
def at_least_one(bool_vars):
    return Or(bool_vars)

def at_most_one(bool_vars):
    return [Not(And(pair[0], pair[1])) for pair in combinations(bool_vars, 2)]

def exactly_one(bool_vars):
    return at_most_one(bool_vars) + [at_least_one(bool_vars)]

class Sat_Model:
    def __init__(self,  n):
        self.n=n
        self.W=n-1
        self.P=n//2
        self.Teams=range(n)
        self.Weeks=range(self.W)
        self.Periods=range(self.P)

        # match[w][i][j] =true if the team i plays against the team j in the week w
        self.matches =[[[Bool(f"match_{w}_{i}_{j}") for j in self.Teams] for i in self.Teams] for w in self.Weeks]
    
        # home[w][i] = true if the team i plays at home in the week w
        self.homes =[[Bool(f"home_{w}_{i}") for i in self.Teams] for w in self.Weeks]
    
        # period[w][i][p] = true if the team i plays in period p in the week w
        self.periods = [[[Bool(f"period_{w}_{i}_{p}") for p in self.Periods] for i in self.Teams] for w in self.Weeks]

        self.s=Solver()
        self.model_satisfiable_constraints()
    
    def model_satisfiable_constraints(self):
        #Constraints
        # every team plays once per week
        for w in self.Weeks:
            for t in self.Teams:
                opponents=[]
                for opp in self.Teams:
                    if opp!=t:
                        if t<opp:
                            opponents.append(self.matches[w][t][opp])
                        else:
                            opponents.append(self.matches[w][opp][t])
                self.s.add(exactly_one(opponents))

        #Every team plays against each other once in the entire tournament (SRR)
        for i in self.Teams:
            for j in self.Teams:
                if i < j:
                    meetings = [self.matches[w][i][j] for w  in self.Weeks]
                    self.s.add(exactly_one(meetings))

        #Every team plays in exactly one period a week
        for w in  self.Weeks:
            for t in self.Teams:
                self.s.add(exactly_one([self.periods[w][t][p] for   p in self.Periods]))
        
        #Every period contains a match ( 2 teams)
        for w in self.Weeks:
            for p in self.Periods:
                count_teams = Sum([If(self.periods[w][t][p],1,0) for t in self.Teams])
                self.s.add(count_teams == 2)
        
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
                count_teams_period = Sum([If(self.periods[w][t][p],1,0) for w in self.Weeks])
                self.s.add(count_teams_period<= 2)
                


        
    def add_symmetry(self):
        #week permutation
        for w in range(1, self.W):
            prev_opp = Sum([If(self.matches[w-1][0][opp], opp, 0) for opp in range(1, self.n)])
            curr_opp = Sum([If(self.matches[w][0][opp], opp, 0) for opp in range(1, self.n)])
            self.s.add(curr_opp > prev_opp)

    def solve(self, timeout=300, symmetry=False):
        if symmetry:
            self.add_symmetry()

        # We set the timeout
        self.s.set("timeout", timeout * 1000)

        start_time = time.time()

        if self.s.check() == sat:
            solve_time = time.time() - start_time
            m = self.s.model()
            
            # Extract solution
            schedule = {"weeks": []}
            
            for w in self.Weeks:
                week_matches = []
                for i in self.Teams:
                    for j in self.Teams:
                        if i < j and m.evaluate(self.matches[w][i][j]):
                            # Find period
                            period = 0
                            for p in self.Periods:
                                if m.evaluate(self.periods[w][i][p]):
                                    period = p
                                    break
                            
                            # Find home/away
                            home_team =  i if m.evaluate(self.homes[w][i]) else j
                            away_team =j if m.evaluate(self.homes[w][i]) else i
                            
                            week_matches.append({
                                "home_team":home_team,
                                "away_team":away_team,
                                "period":period
                            })
                
                schedule["weeks"].append(week_matches)
            
            return {
                "time": solve_time,
                "feasible": True,
                "schedule": schedule
            }
        else:
            solve_time = time.time() - start_time
            return {
                "time": solve_time,
                "feasible": False,
                "schedule": None
            }
def model_satisfiable_sat(n, symmetry=False, timeout=300, **kwargs):
    assert n%2 ==  0, "Remeber team n is even"
    
    # Using only 1 core
    set_param("parallel.enable",False)
    set_param("parallel.threads.max",1)
    set_param("sat.threads",1)
    
    try:
        sat_model =  Sat_Model(n)
        result =sat_model.solve(timeout=timeout, symmetry=symmetry)
        return result
        
    except Exception as e:
        return {
            "time":timeout,
            "feasible":False,
            "schedule":None
        }

# Test the model
if __name__ == "__main__":
    n = 14 # Number of the teams (must be even)
    
    print("Test")
    print("=" * 50)
    
    # Test without symmetry
    print("1. Basic SAT solver:")
    result1 = model_satisfiable_sat(n, symmetry=False, timeout=60)
    if result1["feasible"]:
        print(f"✓ Solution found in {result1['time']:.2f} seconds")
    else:
        print(f"✗ No solution in {result1['time']:.2f} seconds")
    
    # Test with symmetry breaking
    print("\n2. SAT solver with symmetry breaking:")
    result2 = model_satisfiable_sat(n, symmetry=True, timeout=60)
    if result2["feasible"]:
        print(f"✓ Solution found in {result2['time']:.2f} seconds")
    else:
        print(f"✗ No solution in {result2['time']:.2f} seconds")
    
    # Print one solution if found
    best_result = None
    for result in [result1, result2]:
        if result["feasible"]:
            best_result = result
            break
    
    if best_result:
        print(f"\nSample solution:")
        print("=" * 30)
        for w, week in enumerate(best_result["schedule"]["weeks"]):
            print(f"Week {w + 1}:")
            for match in week:
                home = match["home_team"] + 1
                away = match["away_team"] + 1
                period = match["period"] + 1
                print(f"  Team {home} (H) vs Team {away} (A) - Period {period}")
    else:
        print("\nNo solutions found in any configuration!")