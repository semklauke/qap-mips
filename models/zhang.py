import time
import gurobipy as gp
from gurobipy import GRB

from typing import Any


def solve(
    facilities,
    locations,
    distance,
    flow,
    output=False,
    pool=1,
    timelimit=-1
):
    # QAP Model
    model = gp.Model("qap-zhang")
    # search for multiple solutions ? (if we want to make sure the is ONE optimal solution)
    model.setParam('PoolSearchMode', 2 if pool > 1 else 0)
    model.setParam('PoolSolutions', pool)
    # add timelimit for the solver
    timelimit > 0 and model.setParam('TimeLimit', timelimit)

    # LAP model
    model_lap_max = gp.Model("lap_max")
    model_lap_max.setParam('LogToConsole', 0)
    model_lap_min = gp.Model("lap_min")
    model_lap_min.setParam('LogToConsole', 0)

    ### Variables ###
    # QAP model
    x: dict[Any, gp.Var] = {} # x[loc, f] == 1 means facility `f` is in location `loc`
    sigma: dict[Any, gp.Var] = {} # sigma represents the "cost" induced by placing faciilty `f` on location `loc`
    # LAP moodel
    x_lap_max: dict[Any, gp.Var] = {} # x[loc, f] == 1 means facility `f` is in location `loc`
    x_lap_min: dict[Any, gp.Var] = {} # x[loc, f] == 1 means facility `f` is in location `loc`

    for loc in locations:
        for f in facilities:
            x[loc, f] = model.addVar(vtype=GRB.BINARY, name=f"x_{loc}_{f}")
            sigma[loc, f] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"sigma_{loc}_{f})")
            # x can be cont. in LAP because the constraint matrix is totaly unimod.
            x_lap_max[loc, f] = model_lap_max.addVar(vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name=f"lap_x_{loc}_{f}")
            x_lap_min[loc, f] = model_lap_min.addVar(vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name=f"lap_x_{loc}_{f}")

    # Add constraint: Each facility must be placed exactly once
    model.addConstrs(gp.quicksum(x[loc, f] for loc in locations) == 1 for f in facilities)
    model_lap_max.addConstrs(gp.quicksum(x_lap_max[loc, f] for loc in locations) == 1 for f in facilities)

    # Add constraint: No two facilities can be put in the same location
    model.addConstrs(gp.quicksum(x[loc, f] for f in facilities) <= 1 for loc in locations)
    model_lap_max.addConstrs(gp.quicksum(x_lap_max[loc, f] for f in facilities) <= 1 for loc in locations)

    ### Precompute LAP ####
    print("##### start lap")
    start_time = time.time()

    # precompute LAP results for every `loc` & `f` combination
    min_lap = {}
    max_lap = {}
    for loc, f in x:
        max_lap[loc, f] = lap_max(model_lap_max, x_lap_max, loc, f, flow, distance)
        min_lap[loc, f] = lap_min(model_lap_min, x_lap_min, loc, f, flow, distance, facilities, locations)

    end_time = time.time()
    print(f"# finished in {round(end_time - start_time, ndigits=3)} seconds ")
    model._additional_time = round(end_time - start_time, ndigits=2)

    ### Constraints ###
    for loc, f in x:
        model.addConstr(
            sigma[loc, f] >=
                gp.quicksum(
                    flow[f, f_iter] * distance[loc, loc_iter] * x[loc_iter, f_iter]
                    for loc_iter, f_iter in x.keys()
                )
                - max_lap[loc, f] * (1 - x[loc, f])
                - min_lap[loc, f] * x[loc, f]
        )

    ### Objective ###
    objective = gp.quicksum(sigma[loc, f] + min_lap[loc, f] * x[loc, f] for loc, f in x)
    model.setObjective(objective, GRB.MINIMIZE)

    # Optimize model
    model.optimize()

    if output and model.Status == GRB.OPTIMAL:
        for v in model.getVars():
            if int(v.X) == 1 and 'x_' in v.VarName:
                print(f"{v.VarName} {v.X:g}")

        print(f"Obj: {model.ObjVal:g}")

    return model, x

def lap_max(model: gp.Model, x, loc_fix, f_fix, flow, distance):
    # linear objetive with fix location/facility
    model.setObjective(gp.quicksum(
        flow[f_fix, f] * distance[loc_fix, loc] * x[loc, f]
        for loc, f in x
    ))
    model.ModelSense = GRB.MAXIMIZE
    model.optimize()

    return float(model.ObjVal)

def lap_min(model: gp.Model, x, loc_fix, f_fix, flow, distance, facilities, locations):
    # constrains that exclude conflicts
    c1 = model.addConstrs(gp.quicksum(x[loc, f] for loc in locations if loc != loc_fix) == 1 for f in facilities if f != f_fix)
    c2 = model.addConstrs(gp.quicksum(x[loc, f] for f in facilities if f != f_fix) <= 1 for loc in locations if loc != loc_fix)

    # linear objetive with fix location/facility
    conflicts = confliction_assignments(loc_fix, f_fix, x)
    model.setObjective(gp.quicksum(
        flow[f_fix, f] * distance[loc_fix, loc] * x[loc, f]
        for loc, f in x if (loc, f) not in conflicts
    ))
    model.ModelSense = GRB.MINIMIZE

    # optimize
    model.optimize()
    minObj = float(model.ObjVal)

    # restore model0
    model.remove(c1)
    model.remove(c2)
    model.update()

    return minObj

def confliction_assignments(loc_fix, f_fix, x):
    conflicts = []
    for loc, f in x:
        # can't put other facilities in the same location
        if loc == loc_fix and f != f_fix:
            conflicts.append((loc, f))

        # can't put the facility in other locations
        if f == f_fix and loc != loc_fix:
            conflicts.append((loc, f))

    return conflicts