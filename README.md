# Sports-Tournament-Scheduling-Problem
Project work of the Combinatorial Decision Making and Optimization course for the academic year 2024/2025, which is about  modeling and solving the Sports Tournament Scheduling (STS) problem

# Building the docker
step 1-> moving to the source directory
```
cd source 
```
step 2-> building the docker
```
docker build -t sports-tournament-scheduler . 
```

# Running the docker
To perform all the experiments, run:
```
docker run -it sports-tournament-scheduler
```

Once you run the docker, the menu should pop up with all the different model choices: 

1. CP  - Constraint Programming (MiniZinc)
2. SAT - Boolean Satisfiability (Z3)
3. MIP - Mixed Integer Programming (PuLP)
4. SMT - Satisfiability Modulo Theories (Z3)
5. ALL - Run All Experiments (of multiple team sizes)

For each model it is possible to choose the model first (opt,sat,SB..)  , then the number of teams (even).
For option 5, run all experiments, it will ask the n we want to run, for n>=10 will take a lot of time since it is running on many optimization models.
I suggest trying the all run experiments with n=6 and should finish in very little time.

