from pulp import *
import itertools
import time

def build_mip_optimization_model(n, solver_choice="PULP_CBC_CMD"):
    # Check that the number of teams is even (necessary for round-robin)
    assert n % 2 == 0, "Number of teams (n) must be even"
    
    W = n - 1        # Total number of weeks in the tournament
    P = n // 2       # Number of periods (matches per week)
    Teams = range(n)
    Weeks = range(W)
    Periods = range(P)

    # Setup the solver options, limit time to 300 seconds, and run single-threaded
    solvers = {
        "PULP_CBC_CMD": PULP_CBC_CMD(msg=True, threads=1, timeLimit=300),
        "SCIP_PY": SCIP(msg=True, threads=1, timeLimit=300)
    }
    solver = solvers[solver_choice]

    # Create the optimization model
    model = LpProblem(f"STS_Optimization_MinBreaks_n{n}", LpMinimize)

    # Decision variables:
    # opp[w][t][j] = 1 if team t plays against team j in week w, else 0
    opp = LpVariable.dicts("opp", (Weeks, Teams, Teams), cat="Binary")
    # home[w][t] = 1 if team t is playing at home in week w, else 0
    home = LpVariable.dicts("home", (Weeks, Teams), cat="Binary")
    # period[w][t][p] = 1 if team t plays in period p of week w, else 0
    period = LpVariable.dicts("period", (Weeks, Teams, Periods), cat="Binary")

    # Additional variables to count HH or AA breaks
    # breaks[w][t] = 1 if team t has a break (same home/away status in week w and w+1)
    breaks = LpVariable.dicts("breaks", (range(W - 1), Teams), cat="Binary")

    # CONSTRAINTS:

    # Each team plays exactly one match per week against exactly one opponent (not itself)
    for w in Weeks:
        for t in Teams:
            model += lpSum(opp[w][t][j] for j in Teams if j != t) == 1
            model += opp[w][t][t] == 0  # No team plays itself

    # Matches are symmetric: if team i plays team j, then team j plays team i that week
    for w in Weeks:
        for i in Teams:
            for j in Teams:
                if i != j:
                    model += opp[w][i][j] == opp[w][j][i]

    # Every pair of teams plays exactly once in the whole tournament
    for i in Teams:
        for j in Teams:
            if i < j:
                model += lpSum(opp[w][i][j] for w in Weeks) == 1

    # Each team plays in exactly one period in each week
    for w in Weeks:
        for t in Teams:
            model += lpSum(period[w][t][p] for p in Periods) == 1

    # Each period hosts exactly two teams every week (one match per period)
    for w in Weeks:
        for p in Periods:
            model += lpSum(period[w][t][p] for t in Teams) == 2

    # Across the tournament, each team appears in any period at most twice
    for t in Teams:
        for p in Periods:
            model += lpSum(period[w][t][p] for w in Weeks) <= 2

    # If two teams play each other in a week, they must be assigned to the same period
    for w in Weeks:
        for i in Teams:
            for j in Teams:
                if i != j:
                    for p in Periods:
                        # If opp[w][i][j] == 1 then period[w][i][p] == period[w][j][p]
                        model += period[w][i][p] - period[w][j][p] <= (1 - opp[w][i][j])
                        model += period[w][j][p] - period[w][i][p] <= (1 - opp[w][i][j])

    # Home/Away assignment: If two teams play each other, one must be home and the other away
    for w in Weeks:
        for i in Teams:
            for j in Teams:
                if i < j:
                    # When i and j play, exactly one is home
                    model += home[w][i] + home[w][j] <= 1 + (1 - opp[w][i][j]) * 2
                    model += home[w][i] + home[w][j] >= 1 - (1 - opp[w][i][j]) * 2

    # Optimization objective: count total HH or AA breaks
    for w in range(W - 1):
        for t in Teams:
            # If home[w][t] == home[w+1][t], then breaks[w][t] = 1
            model += home[w][t] + home[w + 1][t] - 2 * breaks[w][t] <= 1
            model += home[w][t] + home[w + 1][t] - 2 * breaks[w][t] >= 0

    # Set the objective: minimize total breaks over all teams and weeks
    model += lpSum(breaks[w][t] for w in range(W - 1) for t in Teams)

    # Lower bound on total breaks: at least n - 2
    model += lpSum(breaks[w][t] for w in range(W - 1) for t in Teams) >= n - 2

    return model, opp, home, period, solver


def extract_and_print_schedule(n, opp, home, period):
    # Helper to display the final schedule in a human-readable format
    W = n - 1
    P = n // 2
    Weeks = range(W)
    Periods = range(P)

    schedule = {w: {} for w in Weeks}

    # Extract matches week by week, period by period
    for w in Weeks:
        pairs_found = set()
        for t1 in range(n):
            for t2 in range(n):
                if t1 != t2 and value(opp[w][t1][t2]) > 0.5 and (t2, t1) not in pairs_found:
                    # Find the period in which team t1 plays in week w
                    p = next((p for p in Periods if value(period[w][t1][p]) > 0.5), None)
                    if p is not None:
                        # Determine which team is home
                        if value(home[w][t1]) > 0.5:
                            schedule[w][p] = (t1, t2)  # t1 home, t2 away
                        else:
                            schedule[w][p] = (t2, t1)  # t2 home, t1 away
                        pairs_found.add((t1, t2))

    # Print the schedule in a nicely formatted way
    print("\nSchedule (Partial or Complete):\n")
    for w in Weeks:
        print(f"Week {w + 1}:")
        for p in sorted(schedule[w]):
            h, a = schedule[w][p]
            print(f"  Team {h + 1} (H) vs Team {a + 1} (A) — Period {p + 1}")
        print()

    # Display how many home games each team has
    print("Home Game Counts Per Team:")
    for t in range(n):
        home_count = sum(value(home[w][t]) > 0.5 for w in Weeks)
        print(f"  Team {t + 1}: {home_count} home games")
    print()

    # Show how often each team appears in each period
    print("Period Appearances Per Team:")
    for t in range(n):
        counts = []
        for p in Periods:
            count = sum(value(period[w][t][p]) > 0.5 for w in Weeks)
            counts.append(f"Period {p + 1}: {count}")
        print(f"  Team {t + 1}: " + ", ".join(counts))
    print()

    # Calculate and print the number of consecutive home or away "breaks" per team
    print("Consecutive Home/Away Breaks Per Team:")
    total_breaks = 0
    for t in range(n):
        breaks = 0
        last = None
        for w in Weeks:
            cur = value(home[w][t]) > 0.5
            if last is not None and last == cur:
                breaks += 1
            last = cur
        print(f"  Team {t + 1}: {breaks} breaks")
        total_breaks += breaks
    print(f"\nTotal Breaks: {total_breaks}")


def solve_and_print(n, solver_choice):
    # Measure the time to solve the MIP model and print results
    start = time.time()
    model, opp, home, period, solver = build_mip_optimization_model(n, solver_choice)
    model.solve(solver)
    elapsed = time.time() - start

    print(f"\nUsing solver: {solver_choice}")
    print(f"Solving Time: {elapsed:.2f} seconds")
    print(f"Solver status: {LpStatus[model.status]}")

    # If optimal solution found, extract and display the schedule
    if LpStatus[model.status] == "Optimal":
        extract_and_print_schedule(n, opp, home, period)
    # If partial feasible solution found (e.g., timeout), still display what is available
    elif LpStatus[model.status] in ["Not Solved", "Undefined"] and any(value(v) is not None for v in model.variables()):
        print(" Partial feasible solution found (timeout or early stop). Displaying available results...")
        extract_and_print_schedule(n, opp, home, period)
    else:
        print(" No feasible schedule")


if __name__ == "__main__":
    n = 2  # Set the number of teams (must be even)
    for solver_name in ["PULP_CBC_CMD", "SCIP_PY"]:
        solve_and_print(n, solver_name)