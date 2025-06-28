% srr break optimality
include "globals.mzn"; 
%include "chuffed.mzn";
% --- parameters
int: n;

set of int: T= 1..n;  % teams even
set of int: W= 1..n-1; % weeks
set of int: P= 1..n div 2; % periods
int: MIN_BREAKS=n-2;
int: MAX_BREAKS=(n-1)*(n-2);
% --- decision variables

array[W,T]  of var T  : opp; % opponent of team t in week w
array[W,T]  of var bool  : h; % 1 home 0 away
array[W,T]  of var P: per; % period in which team plays

%--- objective variable and function
array[2..n-1, T] of var bool: break; % break[w,t] = true if team t has a break after week w

% total_breaks is at least n-2 (the theoretical optimum) and at most n·(n-2)
var MIN_BREAKS..MAX_BREAKS : total_breaks;

constraint
    total_breaks = sum(w in 2..n-1, t in T)(break[w,t]);

% constraints

% Forbids a team playing itself
constraint forall(w in W,t in T) (opp[w,t] != t);

%if team t1 plays t2, t2 plays t1, mutuality, and every team appears once this week
constraint forall(w in W) (
    inverse([opp[w,t] | t in T], [opp[w,t] | t in T])
);

%Both of the opponents must be scheduled on the same period.
constraint forall(w in W, t in T) ( per[w,t] = per[w, opp[w,t]] );

% there is exactly one match per period, 1 team home -  1 away
constraint forall(w in W) (
    global_cardinality([per[w, t] | t in T], P, [2 | _ in P])
);

% SRR-> each team meets every other exactly one time
constraint forall(t in T) (
    alldifferent([opp[w, t] | w in W])
);

% a team can compare in the same period maximum 2 times
constraint forall(t in T, p in P)(
   sum(w in W)(bool2int(per[w,t] = p)) <= 2
);

% Break definition: a break occurs when team t has same home/away status in consecutive weeks
constraint forall(w in 2..n-1, t in T)(
   break[w,t] <-> (h[w-1,t] = h[w,t])
);

%exactly one team is home in each match
constraint forall(w in W, t in T)(
   h[w,t] + h[w,opp[w,t]] = 1
);

%--searches

array[int] of var int  : oppVars = [ opp[w,t] | w in W, t in T ];
array[int] of var int  : perVars = [ per[w,t] | w in W, t in T ];
array[int] of var bool : hVars   = [  h[w,t] | w in W, t in T ];


solve
:: seq_search([
      int_search(oppVars,  dom_w_deg, indomain_min),    
      int_search(perVars,  first_fail, indomain_min),     
      bool_search(hVars,   first_fail, indomain_min)      
  ]) minimize total_breaks;


output [
    "Schedule SRR Tournament (Break Minimization):\n",
    "Total breaks: " ++ show(total_breaks) ++ "\n\n",
    "        "] ++
    ["Week " ++ show(w) ++ if w < n-1 then "  " else "" endif | w in W] ++
    ["\n"] ++
    [if p = 1 then "Period " ++ show(p) else "Period " ++ show(p) endif ++
     concat([let {
         set of int: teams_in_period = {t | t in T where fix(per[w,t]) = p},
         array[int] of int: team_list = [t | t in teams_in_period],
         int: t1 = if length(team_list) >= 1 then team_list[1] else 1 endif,
         int: t2 = if length(team_list) >= 2 then team_list[2] else 1 endif
     } in
     if card(teams_in_period) = 2 then
         " " ++ show(min(t1,t2)) ++ " v " ++ show(max(t1,t2)) ++ " "
     else
         "       "
     endif | w in W]) ++
     "\n" | p in P] ++
     ["\n\nHome/Away Pattern:\n"] ++
     ["Team " ++ show(t) ++ ": " ++ 
      concat([if fix(h[w,t]) then "H" else "A" endif | w in W]) ++
      " (Breaks: " ++ show(sum(w in 2..n-1)(fix(break[w,t]))) ++ ")\n" 
      | t in T];
