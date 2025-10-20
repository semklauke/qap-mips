import gurobipy as gp
from gurobipy import GRB
from itertools import product

def solve(
    facilities,
    locations,
    distance,
    flow,
    output=False,
    pool=1
):
    model = gp.Model("qap-linearv2")
    # search for multiple solutions ? (if we want to make sure the is ONE optimal solution)
    model.setParam('PoolSearchMode', 2 if pool > 1 else 0)
    model.setParam('PoolSolutions', pool)

    x = {} # x[loc, f] == 1 iff. facility `f` is placed on location `loc`
    for loc in locations:
        for f in facilities:
            x[loc, f] = model.addVar(vtype=GRB.BINARY, name=f"x_{loc}_{f}")

    y = {} # y[loc1, loc2, f1, f2] == 1 iff. x[loc1, f1] == x[loc2, f2] == 1
    for loc1, loc2 in product(locations, repeat=2):
        for f1, f2 in product(facilities, repeat=2):
            y[loc1, loc2, f1, f2] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="y_{loc1}_{loc2}_{f1}_{f2}")

    # Set objective
    objective = gp.quicksum(
        flow[f1, f2] *
        distance[loc1, loc2] *
        y[loc1, loc2, f1, f2]
        for loc1, loc2, f1, f2 in y.keys()
    )
    model.setObjective(objective, GRB.MINIMIZE)

    # Add constraint: Each facility must be placed exactly once
    model.addConstrs(gp.quicksum(x[loc, f] for loc in locations) == 1 for f in facilities)

    # Add constraint: No two facilities can be put in the same location
    model.addConstrs(gp.quicksum(x[loc, f] for f in facilities) <= 1 for loc in locations)

    # enforce and on y
    for loc_fix, f_fix in x:
        model.addConstrs(
                gp.quicksum(y[loc, loc_fix, f, f_fix] for loc in locations) == x[loc_fix, f_fix]
                for f in facilities
            )
        model.addConstrs(
                gp.quicksum(y[loc, loc_fix, f, f_fix] for f in facilities) == x[loc_fix, f_fix]
                for loc in locations
            )
        model.addConstrs(
                y[loc_fix, loc, f_fix, f] == y[loc, loc_fix, f, f_fix]
                for loc, f in x.keys()
            )


    # Optimize model
    model.optimize()

    if output and model.Status == GRB.OPTIMAL:
        for v in model.getVars():
            if int(v.X) == 1 and 'x_' in v.VarName:
                print(f"{v.VarName} {v.X:g}")

        print(f"Obj: {model.ObjVal:g}")

    return model, x