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
    pool=1
):
    # QAP Model
    model = gp.Model("qap-xiayuanv1")
    # search for multiple solutions ? (if we want to make sure the is ONE optimal solution)
    model.setParam('PoolSearchMode', 2 if pool > 1 else 0)
    model.setParam('PoolSolutions', pool)

    # LAP model
    model_lap = gp.Model("lap")
    model_lap.setParam('LogToConsole', 0)
    #model_lap.setParam("Method", 1)

    ### Variables ###
    # QAP model
    x: dict[Any, gp.Var] = {} # x[loc, f] == 1 means facility `f` is in location `loc`
    sigma: dict[Any, gp.Var] = {} # sigma represents the "cost" induced by placing faciilty `f` on location `loc`
    # LAP moodel
    x_lap: dict[Any, gp.Var] = {} # x[loc, f] == 1 means facility `f` is in location `loc`

    for loc in locations:
        for f in facilities:
            x[loc, f] = model.addVar(vtype=GRB.BINARY, name=f"x_{loc}_{f}")
            sigma[loc, f] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"sigma_{loc}_{f})")
            # x can be cont. in LAP because the constraint matrix is totaly unimod.
            x_lap[loc, f] = model_lap.addVar(vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name=f"lap_x_{loc}_{f}")

    # Add constraint: Each facility must be placed exactly once
    model.addConstrs(gp.quicksum(x[loc, f] for loc in locations) == 1 for f in facilities)
    model_lap.addConstrs(gp.quicksum(x_lap[loc, f] for loc in locations) == 1 for f in facilities)

    # Add constraint: No two facilities can be put in the same location
    model.addConstrs(gp.quicksum(x[loc, f] for f in facilities) <= 1 for loc in locations)
    model_lap.addConstrs(gp.quicksum(x_lap[loc, f] for f in facilities) <= 1 for loc in locations)

    ### Precompute LAP ####
    print("##### start lap")
    start_time = time.time()

    # precompute LAP results for every `loc` & `f` combination
    min_lap = {}
    max_lap = {}
    for loc, f in x:
        minObj, maxObj = lap(model_lap, x_lap, loc, f, flow, distance)
        max_lap[loc, f] = maxObj
        min_lap[loc, f] = minObj

    end_time = time.time()
    print(f"# finished in {round(end_time - start_time, ndigits=3)} seconds ")
    model._additional_time = round(end_time - start_time, ndigits=2)

    ### Constraints ###
    for loc, f in x:
        conflicts = confliction_assignments(loc, f, x)
        model.addConstr(
            sigma[loc, f] >=
                gp.quicksum(
                    flow[f, f_iter] * distance[loc, loc_iter] * x[loc_iter, f_iter]
                    for loc_iter, f_iter in x.keys() if (loc_iter, f_iter) not in conflicts
                )
                - max_lap[loc, f] * (1 - x[loc, f])
        )
        model.addConstr(sigma[loc, f] >= min_lap[loc, f] * x[loc, f])

    ### Objective ###
    objective = gp.quicksum(sigma[loc, f] for loc, f in x)
    model.setObjective(objective, GRB.MINIMIZE)

    # Optimize model
    model.optimize()

    if output and model.Status == GRB.OPTIMAL:
        for v in model.getVars():
            if int(v.X) == 1 and 'x_' in v.VarName:
                print(f"{v.VarName} {v.X:g}")

        print(f"Obj: {model.ObjVal:g}")

    return model, x

def lap(model: gp.Model, x, loc_fix, f_fix, flow, distance):
    beta = {(loc, f): flow[f_fix, f] * distance[loc_fix, loc] for loc, f in x}
    for conflict in confliction_assignments(loc_fix, f_fix, x):
        beta[conflict] = 0.0

    # linear objetive with fix location/facility
    model.setObjective(gp.quicksum(
        beta[loc, f] * x[loc, f]
        for loc, f in x
    ))
    # force fix assignment
    fix_x = model.addConstr(x[loc_fix, f_fix] == 1)
    # get min obj
    model.ModelSense = GRB.MINIMIZE
    model.optimize()
    minObj = float(model.ObjVal)
    # get max obj
    model.ModelSense = GRB.MAXIMIZE
    model.optimize()
    maxObj = float(model.ObjVal)

    # restore model0
    model.remove(fix_x)
    model.update()

    return minObj, maxObj

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