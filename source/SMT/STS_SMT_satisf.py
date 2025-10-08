from z3 import *
import time
import math
import logging
logger=logging.getLogger(__name__)

def model_satisfiable(n,symmetry=False,timeout=300,**kwargs) :
    
    # using only 1 core
    set_param("parallel.enable",False)
    set_param("parallel.threads.max",1)
    set_param("sat.threads",1)

    timeout_timestamp=time.time()  + timeout
    start_timestamp=time.time()
    try :
        # Param
        W=n - 1            # Total weeks in the tournament
        P=n // 2           # Number of periods per week
        Teams=range(n)
        Weeks=range(W)
        Periods=range(P)

        solver=Solver()

        # Decision variables :
        opp=[Array(f"opp_{w}",IntSort(),IntSort()) for w in Weeks ]
        home=[Array(f"home_{w}",IntSort(),BoolSort()) for w in Weeks ]
        period=[Array(f"period_{w}",IntSort(),IntSort()) for w in Weeks ]

        # Constraints
        for w in Weeks :
            for t in  Teams :
                opp_t=Select(  opp[w],t)
                solver.add(opp_t>=0)
                solver.add(opp_t<n)
                solver.add(opp_t!=t)
                # Enforce reciprocal opponents
                solver.add(Select(opp[w],opp_t)==t)
                # Home/Away opposites
                solver.add(Select(home[w],t)==Not(Select(home[w],opp_t)))
                # Period ranges
                solver.add(Select(period[w],t)>=0)
                solver.add(Select(period[w],t)<P)

        # We ensure that both teams in a match share the same period
        for w in Weeks :
            for t in Teams :
                opp_t=Select(opp[w],t)
                # To avoid redundancy,only enforce when t < opp_t
                solver.add(Implies(t < opp_t,Select(period[w],t)==Select(period[w],opp_t)))

        # Each pair of teams meet exactly one time in the tournament
        for i in Teams :
            for j in Teams :
                if i < j :
                    # Count the number of weeks where i meets j
                    meet_times=[If(Select(opp[w],i)==j,1,0) for w in Weeks]
                    solver.add(Sum(meet_times)==1)

        # For each team and period,the team can appear at most twice in that period over all weeks
        for t in Teams :
            for p in Periods :
                appearances=[]
                for w in Weeks :
                    appearances.append(If(Select(period[w],t)==p,1,0))
                solver.add(Sum(appearances)<=2)

        # there is exactly one match per period,1 team home,1 team away
        for w in Weeks :
            for p in Periods :
                count=Sum([If(Select(period[w],t)==p,1,0) for t in Teams])
                solver.add(count==2)
        
        # Implied constraint : Matches are symmetric
        for w in Weeks :
            for i in Teams :
                for j in Teams :
                    if i!=j :
                        solver.add(
                            Implies(Select(opp[w],i)==j,Select(opp[w],j)==i)
                        )

        # Symmetry breaking
        if symmetry :
            #week permutation
            for w in range(1,W) :
                solver.add(Select(opp[w],0)>Select(opp[w-1],0))

        
        # Searching
        solver.push()

        if time.time()>=timeout_timestamp :
            return {
                "time" : timeout,
                "feasible" : False,
                "schedule" : None
            }
        
        solver.set('timeout',int((timeout_timestamp - time.time()) * 1000))
                
        model=None
        result_check=solver.check()
        
        if result_check==sat :
            model=solver.model()
            logger.debug("Solution found")
            logger.debug("First week opponents :")
            for t in Teams :
                opp_val=model.evaluate(Select(opp[0],t)).as_long()
                home_val=model.evaluate(Select(home[0],t))
                period_val=model.evaluate(Select(period[0],t)).as_long()
                logger.debug(f"  Team {t} : vs Team {opp_val},{'Home' if home_val else 'Away'},Period {period_val}")
            
        elif result_check==timeout :
            logger.debug("Solver timed out.")
        else :
            logger.debug("No solution found.")
        
        end=time.time()
        
        result={
            "time" :end-start_timestamp,
            "feasible" :False,
            "schedule" :None
        }
        
        if model is not None :
            result["feasible"]=True  # We found a solution!
                
            if result["time"] >=timeout :
                result["time"]=timeout
                
            # We extract schedule
            schedule={
                "weeks" :[],
                "home_counter" :[0]*n,
                "period_counter" :[[0] * P for _ in range(n)],
                "breaks" :[0]*n
            }
        # We build weekly schedule
            for w in Weeks :
                week_sch=[]
                printed=set()
                
                for t in   Teams :
                    opp_t=model.evaluate(Select(opp[w],t)).as_long()
                    
                    # Werint each match only once
                    if (opp_t,t) not in printed and(t,opp_t) not in printed :
                        is_home=model.evaluate(Select(home[w],t))
                        p_val=model.evaluate(Select(period[w],t))
                        
                        if p_val is None or not    p_val.is_int() :
                            logger.warning(f"Period not assignd for match that involves team {t+1}")
                            continue
                            
                        p=p_val.as_long()
                        
                        match_info={
                            "week" :   w,
                            "home_team" :t if is_home else opp_t,
                            "away_team" :opp_t if is_home else t,
                            "period" :p
                        }
                        week_sch.append(match_info)
                        
                        # now update thecounters
                        schedule["period_counter"][t][p]+=1
                        schedule["period_counter"][opp_t][p]+=1
                        
                        if  is_home :
                            schedule["home_counter"][t]+=1
                        else  :
                            schedule["home_counter"][opp_t]+=1
                        
                        printed.add((t,    opp_t))
                
                schedule["weeks"].append(week_sch     )
            
            # Calculate the breaks for each team.
            for t in  Teams :
                prev_home=None
                for w in Weeks :
                    curr_home=model.evaluate(Select(home[w],t))
                    if prev_home is not None and curr_home==prev_home :
                        schedule["breaks"][t]+=1
                    prev_home=curr_home
            
            result["schedule"]=schedule
        else :
            result["feasible"]=False
            result["schedule"]=None  
            
            if result["time"] >=timeout :
                result["time"]=timeout
                
        return result
        
    except Exception as e :
        logger.error(f"Error in  : {e}")
        return {
            "time" :timeout,
            "feasible" :False,
            "schedule" :None
        }
        

def print_schedule(result) :

    if not result["feasible"] :
        print(f"no feasible found in {result['time'] :.2f} sec")
        return
    schedule=result["schedule"]
    n=len(schedule["home_counter"])
    P=len(schedule["period_counter"][0])

    print(f"\n feasible found in {result['time'] :.2f}  sec\n")

    # We print weekly schedule
    for w,week in enumerate(schedule["weeks"]) :
        print(f"Week {w + 1} :")
        for match in week :
            home=match["home_team"]+ 1
            away=match["away_team"]+ 1
            period=match["period"]+ 1
            print(f"  team {home} (H) vs team {away} (A) ,Period {period}")
        print()

    print("home game counts for each team :")
    for t in range(n) :
        print(f" team {t + 1} : {schedule['home_counter'][t]} home games")

    print("\nperiod appearances for each team :")
    for t in range(n) :
        counts=schedule['period_counter'][t]
        print(f" the team  {t + 1} : " + ",".join([f"peeriod {p+1} : {counts[p]}"  for p in range(P)]))

    print("\n  home/away breaks for each team :")
    for t in range(n) :
        print(f"  team {t + 1} : {schedule['breaks'][t]} breaks")

    print(f"\ntot number  of the breaks : {sum( schedule['breaks'])}")
    print(f"tot solving time : {result['time'] :.2f}  seconds")