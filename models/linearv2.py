import gurobipy as gp
from gurobipy import GRB
from itertools import product
from typing import Any

def solve(
    facilities,
    locations,
    distance,
    flow,
    settings
):
    model = gp.Model("qap-linearv2")
    # search for multiple solutions ? (if we want to make sure there is only ONE optimal solution)
    model.setParam('PoolSearchMode', 2 if settings.pool > 1 else 0)
    model.setParam('PoolSolutions', settings.pool)
    model.setParam('Threads', settings.num_threads)
    # add timelimit for the solver
    if settings.timelimit > 0:
        model.setParam('TimeLimit', settings.timelimit)

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

    if settings.output and model.Status == GRB.OPTIMAL:
        for v in model.getVars():
            if int(v.X) == 1 and 'x_' in v.VarName:
                print(f"{v.VarName} {v.X:g}")

        print(f"Obj: {model.ObjVal:g}")

    return model, x

def solve_equiv(
    facilities,
    locations,
    distance,
    flow,
    equiv_class_sizes,
    equiv_classes,
    settings
):
    model = gp.Model("qap-linearv2")
    # search for multiple solutions ? (if we want to make sure there is only ONE optimal solution)
    model.setParam('PoolSearchMode', 2 if settings.pool > 1 else 0)
    model.setParam('PoolSolutions', settings.pool)
    model.setParam('Threads', settings.num_threads)
    # add timelimit for the solver
    if settings.timelimit > 0:
        model.setParam('TimeLimit', settings.timelimit)

    x: dict[Any, gp.Var] = {} # x[loc, f] == 1 iff. facility `f` is placed on location `loc`
    for loc in locations:
        for f in facilities:
            x[loc, f] = model.addVar(vtype=GRB.BINARY, name=f"x_{loc}_{f}")

    y: dict[Any, gp.Var] = {} # y[loc1, loc2, f1, f2] == 1 iff. x[loc1, f1] == x[loc2, f2] == 1
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
    c1 = model.addConstrs(gp.quicksum(x[loc, f] for loc in locations) == equiv_class_sizes[f] for f in facilities)

    # Add constraint: No two facilities can be put in the same location
    c2 = model.addConstrs(gp.quicksum(x[loc, f] for f in facilities) == 1 for loc in locations)

    # enforce and on y
    c3, c4, c5 = {}, {}, {}
    for loc_fix, f_fix in x:
        c3[loc_fix, f_fix] = model.addConstrs(
                gp.quicksum(y[loc, loc_fix, f, f_fix] for loc in locations) == x[loc_fix, f_fix] * equiv_class_sizes[f]
                for f in facilities
            )
        c4[loc_fix, f_fix] = model.addConstrs(
                gp.quicksum(y[loc, loc_fix, f, f_fix] for f in facilities) == x[loc_fix, f_fix]
                for loc in locations
            )
        c5[loc_fix, f_fix] = model.addConstrs(
                y[loc_fix, loc, f_fix, f] == y[loc, loc_fix, f, f_fix]
                for loc, f in x.keys()
            )


    # Optimize model
    model.optimize()

    if settings.output and model.Status == GRB.OPTIMAL:
        for v in model.getVars():
            if int(v.X) == 1 and 'x_' in v.VarName:
                print(f"{v.VarName} {v.X:g}")

        print(f"Obj: {model.ObjVal:g}")

    # translate solution of this equiv. model to original model
    if model.Status != GRB.OPTIMAL:
        print("######### Clone model not optimal")
        return model, x # but only when we are optimal

    model._additional_time = model.Runtime

    # fix current model and get rid of vars + constr that are not needed for solution
    for v in model.getVars():
        if v.VarName.startswith("x_"):
            fix_value = round(v.X)
            v.LB = fix_value
            v.UB = fix_value
        else:
            model.remove(v)

    model.remove(c1)
    model.remove(c2)
    for loc, f in x.keys():
        model.remove(c3[loc, f])
        model.remove(c4[loc, f])
        model.remove(c5[loc, f])

    for eq in equiv_classes:
        eq_locations = [l for l in locations if round(x[l, eq[0]].X) == 1]
        for f_new, l_new in zip(eq[1:], eq_locations[1:]):
            # clear clone varible
            x[l_new, eq[0]].LB = 0
            x[l_new, eq[0]].UB = 0
            # create new variable for new facility in equiv class
            for l in locations:
                if l != l_new:
                    x[l, f_new] = model.addVar(vtype=GRB.BINARY, lb=0, ub=0, name=f"x_{l}_{f_new}")
                else:
                    x[l, f_new] = model.addVar(vtype=GRB.BINARY, lb=1, ub=1, name=f"x_{l}_{f_new}")

        x[eq_locations[0], eq[0]].LB = 1
        x[eq_locations[0], eq[0]].UB = 1

    # reoptimize
    model.setParam('DualReductions', 0)
    model.update()
    model.setObjective(0)
    model.optimize()

    if settings.output and model.Status == GRB.OPTIMAL:
        for v in model.getVars():
            if int(v.X) == 1 and 'x_' in v.VarName:
                print(f"{v.VarName} {v.X:g}")

        print(f"Obj: {model.ObjVal:g}")

    if model.Status != GRB.OPTIMAL:
        model.computeIIS()
        model.write('iismodel2.ilp')

    return model, x




