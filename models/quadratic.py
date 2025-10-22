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

def solve_equiv(
    facilities,
    locations,
    distance,
    flow,
    equiv_class_sizes,
    equiv_classes,
    output=False,
    pool=1
):
    print(equiv_classes)
    model = gp.Model("qap-quadratic")
    # search for multiple solutions ? (if we want to make sure the is ONE optimal solution)
    model.setParam('PoolSearchMode', 2 if pool > 1 else 0)
    model.setParam('PoolSolutions', pool)

    x: dict[Any, gp.Var] = {} # x[loc, f] == 1 iff. facility `f` is placed on location `loc`
    for loc in locations:
        for f in facilities:
            x[loc, f] = model.addVar(vtype=GRB.BINARY, name=f"x_{loc}_{f}")

    # Set objective
    objective = gp.quicksum(
        flow[f1, f2] *
        distance[loc1, loc2] *
        x[loc1, f1] * x[loc2, f2]
        for (loc1, f1) in x.keys() for (loc2, f2) in x.keys()
    )
    model.setObjective(objective, GRB.MINIMIZE)

    # Add constraint: Each facility must be placed exactly once
    c1 = model.addConstrs(gp.quicksum(x[loc, f] for loc in locations) == equiv_class_sizes[f] for f in facilities)

    # Add constraint: No two facilities can be put in the same location
    c2 = model.addConstrs(gp.quicksum(x[loc, f] for f in facilities) == 1 for loc in locations)

    # Optimize model
    model.optimize()

    if output and model.Status == GRB.OPTIMAL:
        for v in model.getVars():
            if int(v.X) == 1 and 'x_' in v.VarName:
                print(f"{v.VarName} {v.X:g}")

        print(f"Obj: {model.ObjVal:g}")

    # translate solution of this equiv. model to original model
    if model.Status != GRB.OPTIMAL:
        return model, x # but only when we are optimal

    model._additional_time = model.Runtime

    # fix current model and get rid of constraints
    fix_constr = {}
    for l, f in x:
        fix_value = round(x[l, f].X)
        fix_constr[l, f] = model.addConstr(x[l, f] == fix_value)

    print(f"Num Vars: {len(model.getVars())}")

    eq_locations_list = [[l for l in locations if round(x[l, eq[0]].X) == 1] for eq in equiv_classes]

    for i, eq in enumerate(equiv_classes):
        eq_locations = eq_locations_list[i]
        for f_new, l_new in zip(eq[1:], eq_locations[1:]):
            print("1")
            # clear clone varible
            model.remove(fix_constr[l_new, eq[0]])
            fix_constr[l_new, eq[0]] = model.addConstr(x[l_new, eq[0]] == 0)
            # create new variable for new facility in equiv class
            for l in locations:
                if l != l_new:
                    x[l, f_new] = model.addVar(vtype=GRB.BINARY, name=f"x_{l}_{f_new}")
                    fix_constr[l, f_new] = model.addConstr(x[l, f_new] == 0)
                else:
                    x[l, f_new] = model.addVar(vtype=GRB.BINARY, name=f"x_{l}_{f_new}")
                    fix_constr[l, f_new] = model.addConstr(x[l, f_new] == 1)

        model.remove(fix_constr[eq_locations[0], eq[0]])
        fix_constr[eq_locations[0], eq[0]] = model.addConstr(x[eq_locations[0], eq[0]] == 1)

    model.setParam('DualReductions', 0)
    model.update()
    print(f"Num Vars: {len(model.getVars())}")
    # reoptimize
    model.remove(c1)
    model.remove(c2)
    model.setObjective(0)
    model.update()

    model.write("model.lp")
    model.optimize()

    if output and model.Status == GRB.OPTIMAL:
        for v in model.getVars():
            if int(v.X) == 1 and 'x_' in v.VarName:
                print(f"{v.VarName} {v.X:g}")

        print(f"Obj: {model.ObjVal:g}")

    if model.Status != GRB.OPTIMAL:
        model.computeIIS()
        model.write('iismodel2.ilp')

    return model, x