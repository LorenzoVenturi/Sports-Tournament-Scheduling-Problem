# Sports Tournament Scheduling Problem (CDMO Project)

This project implements a Sports Tournament Scheduling Problem solver using four different approaches: **Mixed Integer Linear Programming (MILP)**, **Boolean Satisfiability (SAT)**, **Satisfiability Modulo Theories (SMT)**, and **Constraint Programming (CP)**.

## Checking the solutions built by the solvers

Validate any solution using the provided checker:

```bash
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 solution_checker.py ../res/MIP"
```

## Getting Started

### 1. Starting Docker

With docker running: 

#### For x86/Intel computers:
```bash
docker compose up -d
```

#### For ARM computers (Apple Silicon M1/M2..):
```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64
docker compose up -d
```

This will build and start the container with all necessary solvers installed.

### 2. Verify Container is Running
```bash
docker ps
```

You should see a container named `cdmo_solvers_container` running.

## Running Experiments

### Single Experiments

You can run individual experiments for each solver type. All commands should be executed from the project root directory. 
The files gets updated/created with the new runs, if the model was already present, the new run of the model will substitute the old in the same position of the old model, not at the end of the file.

#### MILP (Mixed Integer Linear Programming)
```bash
# Satisfiability problem with 6 teams using CBC solver
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 MILP/mip_model.py -n 6 -solver 1"

# Optimization problem with 8 teams using SCIP solver
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 MILP/mip_model.py -n 8 -solver 2 -o"

# Optimization with symmetry breaking using HiGHS solver
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 MILP/mip_model.py -n 6 -solver 3 -o -sb"

# Available solvers: 1=CBC, 2=SCIP, 3=HiGHS: ex. -solver 2
# Add -o for optimization, -sb for symmetry breaking
# -n followed by the number of teams you want to run: ex. -n 8
```

#### SAT (Boolean Satisfiability)
```bash
# Satisfiability with 6 teams using naive pairwise encoding
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 SAT/STS_SAT_satisf.py -n 6 --encoding np"

# Satisfiability with 8 teams using Heule encoding
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 SAT/STS_SAT_satisf.py -n 8 --encoding heule"

# Run both encodings
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 SAT/STS_SAT_satisf.py -n 6 --encoding both"

# -n followed by the number of teams you want to run: ex. -n 8
```

#### SMT (Satisfiability Modulo Theories)
```bash
# Satisfiability problem with 6 teams
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 SMT/smt_model.py -n 6"

# Optimization problem with 8 teams
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 SMT/smt_model.py -n 8 -o"

# Optimization problem with symmetry breaking
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 SMT/smt_model.py -n 6 -o -sb"

# -n followed by the number of teams you want to run: ex. -n 8
# -o for optimization
# -sb for symmetry breaking
```

#### CP (Constraint Programming)
```bash
# List all available CP models with their numbers (1-34)
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 CP/CP_STS.py --models"
```
Output:
Available CP models:
================================================================================

Chuffed Models:
----------------------------------------
 1: Chuffed - Satisfiability Base
 2: Chuffed - Satisfiability First-Fail
 3: Chuffed - Satisfiability Random
 4: Chuffed - Satisfiability Symmetry Breaking Base
 5: Chuffed - Satisfiability Symmetry Breaking First-Fail
 6: Chuffed - Satisfiability Symmetry Breaking Random
 7: Chuffed - Optimization First-Fail
 8: Chuffed - Optimization First-Fail Luby
 9: Chuffed - Optimization Random
10: Chuffed - Optimization Random Luby

Gecode Models:
----------------------------------------
11: Gecode - Satisfiability Base
12: Gecode - Satisfiability First-Fail
13: Gecode - Satisfiability Domain/Weight/Degree Min
14: Gecode - Satisfiability Domain/Weight/Degree Random
15: Gecode - Satisfiability Symmetry Breaking Base
16: Gecode - Satisfiability Symmetry Breaking First-Fail
17: Gecode - Satisfiability Symmetry Breaking DWD Min
18: Gecode - Satisfiability Symmetry Breaking DWD Random
19: Gecode - Optimization Implied First-Fail
20: Gecode - Optimization Implied Domain/Weight/Degree
21: Gecode - Optimization Implied DWD No Symmetry Breaking
22: Gecode - Optimization Implied DWD Luby
23: Gecode - Optimization Implied DWD Luby LNS
24: Gecode - Optimization Implied Base First-Fail No SB
25: Gecode - Optimization Implied Base First-Fail Luby
26: Gecode - Optimization Implied Base First-Fail Luby LNS

OR-Tools Models:
----------------------------------------
27: OR-Tools - Satisfiability Base
28: OR-Tools - Satisfiability First-Fail
29: OR-Tools - Satisfiability Domain/Weight/Degree
30: OR-Tools - Satisfiability Symmetry Breaking Base
31: OR-Tools - Satisfiability Symmetry Breaking First-Fail
32: OR-Tools - Satisfiability Symmetry Breaking DWD
33: OR-Tools - Optimization First-Fail
34: OR-Tools - Optimization Domain/Weight/Degree

```bash
# Run specific CP model with 6 teams using model number
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 CP/CP_STS.py -n 6 --model 1"

# Run optimization model with 6 teams
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 CP/CP_STS.py -n 6 --model 19"

# Run OR-Tools optimization model with 6 teams  
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 CP/CP_STS.py -n 6 --model 33"

# -n for choosing the number of teams
# --model to choose the model
```

**Available CP Models (use `--models` to see full list):**
- **Models 1-10**: Chuffed solver (satisfiability & optimization)
- **Models 11-26**: Gecode solver (satisfiability & optimization) 
- **Models 27-34**: OR-Tools solver (satisfiability & optimization)

Each model number corresponds to a specific combination of:
- Solver type (Chuffed, Gecode, OR-Tools)
- Problem type (satisfiability vs optimization)
- Search strategy (First-Fail, Domain/Weight/Degree, Random, etc.)
- Symmetry breaking options

### Automatic Mode (All Configurations)

Each solver type supports an automatic mode that runs all predefined configurations, all these configurations take several hours to run for high n:

#### MILP - All Configurations
```bash
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 MILP/mip_model.py -a"
```
Runs both satisfiability and optimization problems for teams ∈ {4,6,8,10} with all three solvers (CBC, SCIP, HiGHS).

#### SAT - All Configurations  
```bash
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 SAT/STS_SAT_satisf.py -a"
```
Runs satisfiability problems for teams ∈ {4,6,8,10,12,14,16,18} with both naive pairwise and Heule encodings.

#### SMT - All Configurations
```bash
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 SMT/smt_model.py -a"
```
Runs both satisfiability and optimization problems for teams ∈ {4,6,8,10,12,14,16}.

#### CP - All Configurations
```bash
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && python3.11 CP/CP_STS.py -a"
```
Runs all 34 available CP models (satisfiability and optimization) for teams ∈ {4,6,8,10,12,14} with multiple solvers (Chuffed, Gecode, OR-Tools).

**Quick CP Model Reference:**
- Use `--models` to see all 34 models with descriptions
- Models 1-10: Chuffed solver variants
- Models 11-26: Gecode solver variants  
- Models 27-34: OR-Tools solver variants

### Run All Experiments at Once

To run all four solver types automatically:

```bash
docker exec cdmo_solvers_container bash -c "cd /cdmo/source && bash run_all.sh"
```

This script will sequentially execute:
1. All MILP configurations
2. All SAT configurations  
3. All SMT configurations
4. All CP configurations

**Note**: Running all experiments can take several hours depending on your hardware.

## Stopping Long-Running Commands

If any batch command (with `-a` flag) is taking too long or you need to interrupt the execution:

### Method 1: Keyboard Interrupt
**Press `Ctrl+C` in the terminal** where you started the command. This will terminate the `docker exec` command.

**⚠️ Important**: `Ctrl+C` only stops the Docker command but may not kill the actual Python process running inside the container. The solver process might continue running in the background.

### Method 2: Kill Processes Inside Container  
To completely stop all solver processes running inside the Docker container:

```bash
# Kill all Python processes in the container
docker exec cdmo_solvers_container bash -c "pkill -f python"

```
