from pulp import *
import itertools
import time

def build_mip_satisfiability_model(n, solver_choice="PULP_CBC_CMD", with_symmetry=False):
    # Ensure number of teams is even for round-robin scheduling
    assert n % 2 == 0, "Number of teams (n) must be even"
    
    W = n - 1          # Total weeks in the tournament
    P = n // 2         # Number of periods (matches per week)
    Teams = range(n)
    Weeks = range(W)
    Periods = range(P)

    # Setup solvers with 5-minute time limit and single-thread execution for consistency
    solvers = {
        "PULP_CBC_CMD": PULP_CBC_CMD(msg=True, threads=1, timeLimit=300),
        "SCIP_PY": SCIP(msg=True, threads=1, timeLimit=300)
    }
    solver = solvers[solver_choice]

    # Initialize the model for satisfiability (feasibility) - dummy objective since we only check feasibility
    model = LpProblem(f"STS_Satisfiability_n{n}", LpMinimize)

    # Define decision variables:
    # opp[w][t][j]: 1 if team t plays against team j in week w, else 0
    opp = LpVariable.dicts("opp", (Weeks, Teams, Teams), cat="Binary")
    # home[w][t]: 1 if team t plays at home in week w, else 0
    home = LpVariable.dicts("home", (Weeks, Teams), cat="Binary")
    # period[w][t][p]: 1 if team t plays in period p of week w, else 0
    period = LpVariable.dicts("period", (Weeks, Teams, Periods), cat="Binary")

    # -------------------- Constraints --------------------

    # Each team plays exactly one opponent every week and cannot play against itself
    for w in Weeks:
        for t in Teams:
            model += lpSum(opp[w][t][j] for j in Teams if j != t) == 1
            model += opp[w][t][t] == 0

    # Matches are mutual: if team i plays j, then j plays i in the same week
    for w in Weeks:
        for i in Teams:
            for j in Teams:
                if i != j:
                    model += opp[w][i][j] == opp[w][j][i]

    # Every pair of teams must play exactly once across all weeks
    for i in Teams:
        for j in Teams:
            if i < j:
                model += lpSum(opp[w][i][j] for w in Weeks) == 1

    # Each team appears in exactly one period every week
    for w in Weeks:
        for t in Teams:
            model += lpSum(period[w][t][p] for p in Periods) == 1

    # Each period hosts exactly two teams per week (one match per period)
    for w in Weeks:
        for p in Periods:
            model += lpSum(period[w][t][p] for t in Teams) == 2

    # No team can appear more than twice in any single period across the tournament
    for t in Teams:
        for p in Periods:
            model += lpSum(period[w][t][p] for w in Weeks) <= 2

    # If two teams play each other in a week, they must be assigned to the same period
    for w in Weeks:
        for i in Teams:
            for j in Teams:
                if i != j:
                    for p in Periods:
                        model += period[w][i][p] - period[w][j][p] <= (1 - opp[w][i][j])
                        model += period[w][j][p] - period[w][i][p] <= (1 - opp[w][i][j])

    # Home/Away assignment: teams playing each other must have opposite home status
    for w in Weeks:
        for i in Teams:
            for j in Teams:
                if i < j:
                    model += home[w][i] + home[w][j] <= 1 + (1 - opp[w][i][j]) * 2
                    model += home[w][i] + home[w][j] >= 1 - (1 - opp[w][i][j]) * 2

    # Optional symmetry breaking to reduce equivalent solutions:
    # Team 0's opponents must be in ascending order across weeks to break symmetry
    if with_symmetry:
        for w in range(W - 1):
            for j in range(1, n):
                model += lpSum(opp[w][0][x] for x in range(j + 1)) >= opp[w + 1][0][j]

    return model, opp, home, period, solver


def extract_and_print_schedule(n, opp, home, period):
    # Prepare some useful parameters
    W = n - 1
    P = n // 2
    Weeks = range(W)
    Periods = range(P)

    # Build the schedule dictionary to hold matches per week and period
    schedule = {w: {} for w in Weeks}

    # Go through all teams and weeks, extracting matchups and periods from the solution variables
    for w in Weeks:
        pairs_found = set()
        for t1 in range(n):
            for t2 in range(n):
                if t1 != t2 and value(opp[w][t1][t2]) > 0.5 and (t2, t1) not in pairs_found:
                    # Find which period team t1 plays in this week
                    p = next((p for p in Periods if value(period[w][t1][p]) > 0.5), None)
                    if p is not None:
                        # Determine home team for display
                        if value(home[w][t1]) > 0.5:
                            schedule[w][p] = (t1, t2)  # t1 is home, t2 is away
                        else:
                            schedule[w][p] = (t2, t1)  # t2 is home, t1 is away
                        pairs_found.add((t1, t2))

    # Print the match schedule in a readable format
    print("\nSchedule (Partial or Complete):\n")
    for w in Weeks:
        print(f"Week {w + 1}:")
        for p in sorted(schedule[w]):
            h, a = schedule[w][p]
            print(f"  Team {h + 1} (H) vs Team {a + 1} (A) — Period {p + 1}")
        print()

    # Show how many home games each team has in the schedule
    print("Home Game Counts Per Team:")
    for t in range(n):
        home_count = sum(value(home[w][t]) > 0.5 for w in Weeks)
        print(f"  Team {t + 1}: {home_count} home games")
    print()

    # Display the number of appearances of each team in each period across all weeks
    print("Period Appearances Per Team:")
    for t in range(n):
        counts = []
        for p in Periods:
            count = sum(value(period[w][t][p]) > 0.5 for w in Weeks)
            counts.append(f"Period {p + 1}: {count}")
        print(f"  Team {t + 1}: " + ", ".join(counts))
    print()

    # Count and display the number of consecutive home or away games ("breaks") per team
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


def solve_and_print(n, solver_choice, with_symmetry=False):
    # Track solving time to assess performance
    start = time.time()
    model, opp, home, period, solver = build_mip_satisfiability_model(n, solver_choice, with_symmetry)
    model.solve(solver)
    elapsed = time.time() - start

    print(f"\nUsing solver: {solver_choice} | Symmetry breaking: {with_symmetry}")
    print(f"Solving Time: {elapsed:.2f} seconds")
    print(f"Solver status: {LpStatus[model.status]}")

    # Print the schedule if optimal or partially feasible solution was found
    if LpStatus[model.status] == "Optimal":
        extract_and_print_schedule(n, opp, home, period)
    elif LpStatus[model.status] in ["Not Solved", "Undefined"] and any(value(v) is not None for v in model.variables()):
        print("Partial feasible solution found (timeout or early stop). Displaying available results...")
        extract_and_print_schedule(n, opp, home, period)
    else:
        print("No feasible schedule")


if __name__ == "__main__":
    n = 12  # Adjust the number of teams here (must be even)
    for solver_name in ["PULP_CBC_CMD", "SCIP_PY"]:
        solve_and_print(n, solver_name, with_symmetry=True)