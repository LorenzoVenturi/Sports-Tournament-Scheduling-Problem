from pulp import *
import itertools
import time

def satisfiability_milp_model(n,solver_choice="PULP_CBC_CMD"):
    """
    Function to build the model for STS
    """
    #Check n even
    assert n%2== 0, "N must be even"
    
    #parameters
    W = n-1        #number of weeks in the tournament
    P = n//2       #number of periods (matches per week)
    Teams = range(n)
    Weeks = range(W)
    Periods = range(P)

    #dictionary to store the different solver we want to use
    solvers = {
    "PULP_CBC_CMD": PULP_CBC_CMD(msg=False, threads=1, timeLimit=300),#we keep 1 thread, 5 min limits
    "SCIP_PY": SCIP_PY(msg=False, timeLimit=300),
    "HiGHS": HiGHS(msg=False,threads=1, timeLimit=300)  
    }

    #we extract the solver
    solver = solvers[solver_choice]

    #we define here the model
    model = LpProblem(f"STS_Sat_n{n}", LpMinimize)

    #We define the decision variables
    #opp[w][t][j]= 1 if team t1 plays against team j1 in week w
    opp =  LpVariable.dicts("opp",(Weeks,Teams,Teams),cat="Binary")
    #home[w][t]= 1 if team t1 plays at home in week w
    home =LpVariable.dicts("home",(Weeks, Teams),cat="Binary")
    #period[w][t][p]= 1 if team t plays in period p of week w
    period =  LpVariable.dicts("period",(Weeks,Teams,Periods),cat="Binary")


    #We define the Constraints

    #each team plays exactly one match per week against exactly one opponent (not itself)
    for w in Weeks:
        for t in Teams:
            model += lpSum(opp[w][t][j] for j in Teams if j != t) == 1
            model += opp[w][t][t] == 0 #implied 1

    #implied 2-> matches are symmetric: if team i plays team j, then team j plays team i that week
    for w in Weeks:
        for i in Teams:
            for j in Teams:
                if i!=j:
                    model+=opp[w][i][j]==opp[w][j][i]

    #every pair of  teams plays exactly oone time in the entire tournament
    for i in Teams:
        for j in Teams:
            if i < j:
                model +=lpSum(opp[w][i][j] for w in Weeks)==1

    #each team plays   in exactly one period in each week
    for w in Weeks:
        for t in Teams:
            model+=lpSum(period[w][t][p] for p in Periods)==1

    #each  period hosts exactly two teams every week (one match per period)
    for w in Weeks:
        for p in Periods:
            model+=lpSum(period[w][t][p] for t in Teams)==2

    #each team appears in any period at most 2 times in the entire tournament
    for t in Teams:
        for p in Periods:
            model +=lpSum(period[w][t][p] for w in Weeks) <= 2

    #if two teams play each other in a week, they must be assigned to the same period
    for w in Weeks:
        for i in Teams:
            for j in Teams:
                if i != j:
                    for p in Periods:
                        model+=period[w][i][p]- period[w][j][p]<=(1-opp[w][i][j])
                        model += period[w][j][p]- period[w][i][p]<=(1-opp[w][i][j])

    #if two teams play each other, one must be home and the other away
    for w in Weeks:
        for i in Teams:
            for j in Teams:
                if i<j:
                    model+=home[w][i] +home[w][j]<=1+(1-opp[w][i][j])*  2
                    model+=home[w][i] +home[w][j]>=1-(1-opp[w][i][j])*  2


    return model,opp,home,period,solver


def extract_and_print_schedule(n,opp,home,period):
    """
    Function to print the tournament schedule that the model found
    """
    W=n-1
    P=n//2
    Weeks=range(W)
    Periods=range(P)

    schedule = {w:  {} for w in Weeks}

    for w in  Weeks:
        found=   set()
        for t1 in  range(n):
            for t2 in  range(n):
                if t1!=t2 and   value(opp[w][t1][t2])>0.5 and (t2,t1) not in found:
                    p =   next((p for p in Periods if value(period[w][t1][p]) >   0.5), None)
                    if p  is not None:
                        if  value(home[w][t1])>0.5:
                            schedule[w][p] =(t1, t2)  #t1 home-> t2 away
                        else :
                            schedule[w][p] =(t2, t1)  #t2 home-> t1 away
                        found.add((t1, t2))

    print("\nSchedule\n")
    for w in Weeks:
        print(f"Week {w + 1}:")
        for p in sorted(schedule[w]):
            h, a = schedule[w][p]
            print(f"  Team {h + 1} (home) vs Team {a + 1} (away) —> Period {p + 1}")
        print()

    print("home game counts for team:")
    for t in range(n):
        home_count = sum(value(home[w][t]) > 0.5 for w in Weeks)
        print(f"  team {t + 1}: {home_count} home games")
    print()

    print("period appearances for team:")
    for t in range(n):
        counts = []
        for p in Periods:
            count = sum(value(period[w][t][p]) > 0.5 for w in Weeks)
            counts.append(f"Period {p + 1}: {count}")
        print(f"  Team {t + 1}: " + ", ".join(counts))
    print()



def solve_and_print(n, solver_choice):
    """
    Utils function to solve and print the problem"""
    start = time.time()
    model,opp,home,period,solver=satisfiability_milp_model(n,solver_choice)
    model.solve(solver)
    elapsed = time.time()-start

    print(f"\nusing solver: {solver_choice}")
    print(f"solving Time: {elapsed:.2f} seconds")

    if LpStatus[model.status] in ["Optimal","Feasible","Suboptimal"]:
        extract_and_print_schedule(n, opp, home, period)
    else:
        print( " no feasible schedule has been found ")


if __name__   ==   "__main__":
    n = 4
    for  solver_name in [ "PULP_CBC_CMD","SCIP_PY","HiGHS" ]:
        solve_and_print(n,solver_name )