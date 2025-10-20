import gurobipy as gp
from gurobipy import GRB

def solve(
    facilities,
    locations,
    distance,
    flow,
    output=False,
    pool=1
):
    model = gp.Model("qap-quadratic")
    # search for multiple solutions ? (if we want to make sure the is ONE optimal solution)
    model.setParam('PoolSearchMode', 2 if pool > 1 else 0)
    model.setParam('PoolSolutions', pool)

    x = {} # x[loc, f] == 1 iff. facility `f` is placed on location `loc`
    for loc in locations:
        for f in facilities:
            x[loc, f] = model.addVar(vtype=GRB.BINARY, name=f"x_{loc}_{f}")

    # Set quadratic objective
    objective = gp.quicksum(
        flow[f1, f2] *
        distance[loc1, loc2] *
        x[loc1, f1] * x[loc2, f2]
        for (loc1, f1) in x.keys() for (loc2, f2) in x.keys()
    )
    model.setObjective(objective, GRB.MINIMIZE)

    # Add constraint: Each facility must be placed exactly once
    model.addConstrs(gp.quicksum(x[loc, f] for loc in locations) == 1 for f in facilities)

    # Add constraint: No two facilities can be put in the same location
    model.addConstrs(gp.quicksum(x[loc, f] for f in facilities) <= 1 for loc in locations)

    # Optimize model
    model.optimize()

    if output and model.Status == GRB.OPTIMAL:
        for v in model.getVars():
            if int(v.X) == 1 and 'x_' in v.VarName:
                print(f"{v.VarName} {v.X:g}")

        print(f"Obj: {model.ObjVal:g}")

    return model, x