include "globals.mzn";

% --- Model parameters ---

int: n_Teams;  %even number of teams
int: n_Rounds = n_Teams - 1;
int: n_Matches = n_Teams div 2; 

set of int: TEAMS   = 1..n_Teams;
set of int: ROUNDS   = 1..n_Rounds;

int: min_home = n_Rounds div 2; % since odd teams, n-1 rounds, some teams will have +1 home game, other -1.
int: max_home = min_home + 1;


% --- Decision Variables ---

% -- Phase 1 --
array[TEAMS, ROUNDS] of var {0,1}: HAP;   % 0=home / 1=away

% -- Phase 2 --
array[ROUNDS, TEAMS] of var TEAMS: opp;   % opponent of team t in week w

% --- Objective ---
array[TEAMS] of var 0..(n_Rounds-1): breaks;      % per-team break count

var 0..n_Teams*(n_Rounds-1): total_breaks =        % total breaks
        sum(t in TEAMS)(breaks[t]);
        
%---constraints---
%-phase 1-
constraint forall(r in ROUNDS)(
  sum(t1 in TEAMS)(1 - HAP[t1,r]) = n_Matches   
);


constraint forall(t1 in TEAMS)(
  let {var int: homes = sum(r1 in ROUNDS)(1 - HAP[t1,r1])}
  in homes>=min_home /\ homes<=max_home
);

constraint forall(t in TEAMS)(                     
  breaks[t]=sum(r1 in 1..n_Rounds-1)(
                 bool2int(HAP[t,r1] = HAP[t,r1+1]))
);

%--phase 2--
% no self game
constraint forall(r in ROUNDS, t in TEAMS)(
  opp[r,t] != t
);

% Opponent relationship is symmetric
constraint forall(r in ROUNDS, t1 in TEAMS, t2 in TEAMS where t1 < t2)(
  (opp[r,t1] = t2) <-> (opp[r,t2] = t1)
);

% Every unordered pair appears exactly once over all rounds (meet-once)
constraint forall(t1,t2 in TEAMS where t1 < t2)(
  sum(r in ROUNDS)( bool2int(opp[r,t1] = t2) ) = 1
);

% Home/away consistency: paired teams must have opposite HAP statuses
constraint forall(r in ROUNDS, t1 in TEAMS, t2 in TEAMS where t1 < t2)(
  (opp[r,t1] = t2) -> (HAP[t1,r] != HAP[t2,r])
);

%---Symmetry breaking constraints---
constraint HAP[1,1] = 0;                 % team 1 home in round 1
constraint forall(r in ROUNDS)(          % team 1 plays 2,3,… in order
  opp[r,1] = r + 1
);
constraint forall(t in TEAMS where t > 1)(
  breaks[1] <= breaks[t]                 % team 1 has min breaks
);

%======================================================================
%                         TWO-PHASE SEARCH
%======================================================================
solve::
  seq_search([
   int_search(
       [HAP[t,r] | t in TEAMS, r in ROUNDS],
       first_fail,
       indomain_min, % indomain_split is okay, but indomain_min is equivalent for binary variables
       complete
     ),
   int_search(
       [opp[r,t] | r in ROUNDS, t in TEAMS],
       first_fail,
       indomain_min, % For finding pairs, indomain_min/max can be effective
       complete
     )
     ])
  minimize total_breaks;