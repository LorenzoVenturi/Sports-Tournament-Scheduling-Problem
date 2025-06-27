%SRR satisfiability
include "globals.mzn";
 
% --- parameters
int: n; % even

set of int: T= 1..n;  % teams even
set of int: W= 1..n-1; % weeks
set of int: P= 1..n div 2; % periods

% --- decision variables
array[W,T]  of var T  : opp; % opponent of team t in week w
array[W,T]  of var P: per; % period in which team plays
array[W,T] of var bool : h; 
  
% --- constraints

% Forbids a team playing itself
constraint forall(w in W,t in T) (opp[w,t] != t);

% If team t1 plays t2, t2 plays t1, mutuality, and every team appears once a week
constraint forall(w in W) (
    inverse([opp[w,t] | t in T], [opp[w,t] | t in T])
);

%Both of the opponents must be scheduled on the same period.
constraint forall(w in W, t in T) (per[w,t] =per[w, opp[w,t]] );

% there is exactly one match per period, 1 team home -  1 team away
constraint forall(w in W) ( global_cardinality([per[w, t] | t in T], P, [2 | _ in P]) );

% each team meets every other exactly one time
constraint forall(t in T) ( alldifferent([opp[w, t] | w in W]) );
  
% a team can compare in the same period maximum 2 times over all the weeks
constraint
  forall(t in T) (
      global_cardinality_low_up([per[w,t] | w in W],P,                             
                                                   [0 | _ in P],                   % lower bounds  0
                                                   [2 | _ in P]));                    % upper bounds  2

% In any game, exactly one team is home and the other is away.
constraint forall(w in W, t in T) (
   h[w,t] + h[w, opp[w,t]] = 1);
   
% --- simmetry breaking constraints

% week permutation
constraint
   forall(w in 2..n-1)(opp[w,1] > opp[w-1,1]);
   


solve :: seq_search([
    int_search(opp, dom_w_deg, indomain_random),
    int_search(per, dom_w_deg, indomain_random),
    bool_search(h,input_order, indomain_min)
]) satisfy;

output [
    "Schedule SRR Tournament :\n",
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
     "\n" | p in P];
