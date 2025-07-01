from z3 import *
import time
import math
import logging
logger =logging.getLogger(__name__)

def millisecs_left(current_time,timeout_timestamp):
    remaining =timeout_timestamp-current_time
    return max(0,int(remaining*1000))

def model_optimized(n,symmetry=False,  timeout=300,**kwargs):
    
    # using only 1 core
    set_param("parallel.enable",False)
    set_param("parallel.threads.max",1)
    set_param("sat.threads",1)

    timeout_timestamp = time.time()+timeout
    start_timestamp = time.time()
    
    try:

        # Parameters
        W = n-1            # Total weeks in the tournament
        P = n//2           # Number of periods per week
        Teams= range(n)
        Weeks= range(W)
        Periods= range(P)

        solver= Optimize()

        # decision variables
        opp= [Array(f"opp_{w}",IntSort(), IntSort()) for w in Weeks]
        home= [Array(f"home_{w}",IntSort(), BoolSort()) for w in Weeks]
        period= [Array(f"period_{w}",IntSort(), IntSort()) for w in Weeks]
        
        # Break variables for each teams
        breaks = [Int(f"breaks_{t}") for t in Teams]

        # constraints
        for w in Weeks:
            for t in Teams:
                opp_t = Select(opp[w], t)
                solver.add(opp_t >= 0)
                solver.add(opp_t < n)
                solver.add(opp_t!= t)
                # Enforce reciprocal opponents
                solver.add(Select(opp[w],opp_t)==t)
                # Home/Away opposites
                solver.add(Select(home[w],t) == Not(Select(home[w], opp_t)))
                # Period in range
                solver.add(Select(period[w],t)>= 0)
                solver.add(Select(period[w],t) < P)

        # Ensure both teams in a match share the same period
        for w in Weeks:
            for t in Teams:
                opp_t =Select(opp[w],t)
                solver.add(Implies(t<opp_t,Select(period[w],t)== Select(period[w],opp_t)))

        # Each pair of teams meet exactly one time in the tournament
        for i in Teams:
            for j in Teams:
                if i < j:
                    meet_times = [If(Select(opp[w],i)==j,1,0) for w in Weeks]
                    solver.add(Sum(meet_times)==1)

        # For each team and period, the team can appear at most twice in that period over all weeks
        for t in Teams:
            for p in Periods:
                appearances = [If(Select(period[w],t)==p,1,0) for w in Weeks]
                solver.add(Sum(appearances)<=2)

        # Exactly one match per period (2 teams per period)
        for w in Weeks:
            for p in Periods:
                count = Sum([If(Select(period[w],t)==p,1,0) for t in Teams])
                solver.add(count == 2)
        
        # breaks
        for t in Teams:
            # We calculate the breaks for each team
            team_breaks = []
            for w in range(1, W):
                prev_home =Select(home[w-1],t)
                curr_home =Select(home[w],t)
                team_breaks.append(If(prev_home == curr_home, 1, 0))
            
            # breaks[t] = sum of all breaks for team t
            solver.add(breaks[t]==  Sum(team_breaks))
            solver.add(breaks[t]>=  0)
        
        # Implied constraint Matches are symmetric
        for w in Weeks:
            for i in Teams:
                for j in Teams:
                    if i != j:
                        solver.add(
                            Implies(Select(opp[w],i)==j,Select(opp[w],j)== i))

        # Symmetry breaking (optional)
        if symmetry:
            # Fix first match: Team 0 vs Team 1 in week 0, Team 0 at home
            solver.add(Select(opp[0], 0) == 1)
            solver.add(Select(home[0], 0) == True)
            
            # Week permutation: opponents of team 0 in increasing order
            for w in range(1, W):
                solver.add(Select(opp[w], 0) > Select(opp[w-1], 0))

        # objective function
        obj = Int('total_breaks')
        solver.add(obj == Sum(breaks))
        
        # upper and lower bounds
        # Lower bound
        solver.add(obj >= max(0, n-2))  # At least n-2 total breaks
        
        # Upper bound
        solver.add(obj <= (n-2) * (n-1))

        # Manual optimization loop to show intermediate results
        best_obj = None
        best_model = None
        iteration = 0
        
        logger.debug("Starting manual optimization loop...")
        start = time.time()
        
        while time.time() < timeout_timestamp:
            iteration += 1
            remaining_time = int((timeout_timestamp - time.time()) * 1000)
            if remaining_time <= 0:
                break
                
            solver.set('timeout',remaining_time)
            
            result_check = solver.check()
            current_time = time.time()
            
            if result_check==sat:
                model= solver.model()
                current_obj =model[obj].as_long()
                
                if best_obj is None or current_obj<best_obj:
                    best_obj =current_obj
                    best_model =model
                    
                    # Print intermediate result
                    print(f"\nIntermediate Result(Iteration {iteration}):")
                    print(f"Current best: {current_obj} total breaks")
                    print(f"Time elapsed: {current_time - start:.2f} seconds")
                    
                # We add the constraint to find better solution
                solver.add(obj < current_obj)
                
            elif result_check==unsat:
                logger.debug(f"No better solution (iteration{iteration})")
                break
            elif result_check==timeout:
                logger.debug(f"Timeout in  {iteration}")
                break
            else:
                logger.debug(f"Unknown result: {result_check}")
                break
        
        end = time.time()
        
        if best_model is not None:
            result_check =sat
            final_model =best_model
            final_obj =best_obj
        else:
            result_check = unsat if iteration > 1 else timeout
            final_model = None
            final_obj = None
        
        # Result processing
        result = {
            "time": end - start_timestamp,
            "optimal": False,
            "obj": None,
            "schedule": None
        }
        
        if result_check == sat:
            model = final_model
            result_objective = final_obj
            
            # We Check if we found the optimal solution (no timeout occurred)
            result["optimal"] = (end - start) < timeout
            result["obj"] = result_objective
            
            # Extract the schedule
            schedule = {
                "weeks":[],
                "home_counts":[0] * n,
                "period_counts":[[0] * P for _ in range(n)],
                "breaks":[model[breaks[t]].as_long() for t in Teams]
            }
            
            # Build the schedule
            for w in Weeks:
                week_schedule=[]
                printed =  set()
                
                for t in Teams:
                    opp_t = model.evaluate(Select(opp[w],t)).as_long()
                    
                    if (opp_t,t)   not in printed and   (t,opp_t) not in printed:
                        is_home =   model.evaluate(Select(home[w],  t))
                        p_val =   model.evaluate(Select(period[w],  t))
                        
                        if p_val  is None or not  p_val.is_int():
                            logger.warning(f"Period not assigned for match involving team{t+1}")
                            continue
                            
                        p =  p_val.as_long()
                        
                        match_info ={
                            "week":   w,
                            "home_team":t if     is_home else opp_t,
                            "away_team":opp_t if is_home else t,
                            "period":p
                        }
                        week_schedule.append(match_info)
                        
                        # Update counters
                        schedule["period_counts" ][t][p]+= 1
                        schedule["period_counts" ][opp_t][p]+= 1
                        
                        if  is_home:
                            schedule["home_counts"][t] += 1
                        else:
                            schedule["home_counts"][opp_t] += 1
                        
                        printed.add((t, opp_t))
                
                schedule["weeks"].append(week_schedule)
            
            result["schedule"] = schedule
            
        elif result_check==   timeout or  result_check== unsat:
            if best_model is not   None:
                # We have a feasible solution from earlier iterations
                logger.info(f"Timeout, Using the best solution found: {best_obj} total breaks")
                result["time"]= end - start_timestamp
                result["optimal"]= False
                result["obj"]=   best_obj

                # Extract the schedule from the best Model
                model = best_model
                schedule = {
                    "weeks":  [],
                    "home_counts":[0] * n,
                    "period_counts":[[0]*P for _ in range(n)],
                    "breaks":  [model[breaks[t]].as_long() for t in Teams]
                }

                for w in Weeks:
                    week_schedule =  []
                    printed =   set()

                    for t in   Teams:
                        opp_t =   model.evaluate(Select(opp[w],   t)).as_long()

                        if (opp_t,   t) not in printed and (t, opp_t) not in printed:
                            is_home = model.evaluate(Select(home[w],  t))
                            p_val =  model.evaluate(Select(period[w], t))

                            if p_val   is None or not p_val.is_int():
                                continue

                            p = p_val.as_long()

                            match_info = {
                                "week":  w,
                                "home_team": t if  is_home else opp_t,
                                "away_team": opp_t if  is_home else t,
                                "period": p
                            }
                            week_schedule.append(match_info)

                            schedule["period_counts"][t][p]  += 1
                            schedule["period_counts"][opp_t][p]  += 1

                            if is_home:
                                schedule["home_counts"][t]   += 1
                            else:
                                schedule["home_counts"][opp_t]   += 1

                            printed.add((t, opp_t))

                    schedule["weeks"].append(week_schedule)

                result["schedule"] = schedule
            else:
                logger.info("TIMEOUT: No solution is found")
                result["time"] =  end - start_timestamp
                result["optimal"] =  False
                result["obj"] =  None
                result["schedule"] =   None

        else:
            logger.debug(f"No solution is found, the solver returned {result_check}")
            result["optimal"] = False

        return result
        
    except Exception as e:
        logger.error(f"Error in STS_SMT_opt:{e}")
        return {
            "time":timeout,
            "optimal":False,
            "obj":None,
            "schedule":None
        }

def print_schedule(result):
    
    if not result["optimal"] and result["obj"] is None:
        print(f"No feasible schedule found in {result['time']:.2f} seconds.")
        return

    schedule = result["schedule"]
    n = len(schedule["home_counts"])
    P = len(schedule["period_counts"][0])
    
    if result["optimal"]:
        print(f"\opt: Schedule Found in {result['time']:.2f} seconds!")
    else:
        print(f"\timeout: Best schedule found in {result['time']:.2f} seconds")
    
    print(f"Total Breaks: {result['obj']}\n")

    # Print weekly schedule
    for w, week in enumerate(schedule["weeks"]):
        print(f"Week {w + 1}:")
        for match in week:
            home = match["home_team"]+ 1
            away = match["away_team"] +1
            period = match["period"]+ 1
            print(f"  Team {home} (H) vs Team {away} (A) — Period {period}")
        print()

    # Print summaries
    print("Home Game Counts Per Team:")
    for t in range(n):
        print(f"  Team {t + 1}: {schedule['home_counts'][t]} home games")

    print("\n⏱ Period Appearances Per Team:")
    for t in range(n):
        counts = schedule['period_counts'][t]
        print(f"  Team {t + 1}: " + ", ".join([f"Period {p+1}: {counts[p]}" for p in range(P)]))

    print("\nConsecutive Home/Away Breaks Per Team:")
    for t in range(n):
        print(f"Team {t+1}: {schedule['breaks'][t]} breaks")

    print(f"\nTotal Breaks: {result['obj']}")
    print(f"Total Solving Time: {result['time']:.2f} seconds")
    print(f"Solution Status: {'OPTIMAL' if result['optimal'] else 'FEASIBLE (timeout)'}")

#run the model
if __name__ == "__main__":
    n = 12     
    mode = 1   # 0 = base (with implied), 1 = base + symmetry breaking
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

    result = model_optimized(
        n,
        symmetry=(mode == 1),
        timeout=300
    )

    print_schedule(result)