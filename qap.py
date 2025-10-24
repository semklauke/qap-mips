#!/usr/bin/env python3

import argparse, os, sys
import pkgutil
from importlib import util, import_module
from itertools import product, filterfalse, pairwise

from gurobipy import GRB

# import models
models = {
    module_name : import_module(f"models.{module_name}")
    for _, module_name, _ in pkgutil.iter_modules(["models"])
}


def main():
    parser = create_argparser()
    args = parser.parse_args()
    models_to_run = [m.strip() for m in args.models.strip().split(',') if m]

    # Check that the instance file exists.
    if not os.path.exists(args.instance_file):
        parser.error(f"Error: The file '{args.instance_file}' does not exist.")

    # load the instance file
    instance_name = os.path.splitext(os.path.basename(args.instance_file))[0]
    print(args.instance_file, instance_name)
    instance = import_from_string(instance_name, args.instance_file)

    if args.merge_clones:
        diff = remove_clone_facilities(instance)
        if diff <= 0: exit(1)

    ##### solve
    objective_values = {}
    positions = {}
    runtimes = {}
    statuses = {}

    for model_name in models_to_run:
        if args.merge_clones:
            model, x = models[model_name].solve_equiv(
                instance.clone_facilities,
                instance.locations,
                instance.distance,
                instance.clone_flow,
                instance.equiv_class_sizes,
                instance.equiv_classes,
                args.output,
                args.pool,
                args.timelimit,
            )
        else:
            model, x = models[model_name].solve(
                instance.facilities,
                instance.locations,
                instance.distance,
                instance.flow,
                args.output,
                args.pool,
                args.timelimit
            )

        statuses[model_name] = model.Status

        if model.Status != GRB.OPTIMAL:
            print(f"{model_name} model not optimal.")
        else:
            true_obj = sum([
                instance.flow[f1, f2] *
                instance.distance[loc1, loc2] *
                round(x[loc1, f1].X) *
                round(x[loc2, f2].X)
                for loc1 in instance.locations
                for loc2 in instance.locations
                for f1 in instance.facilities
                for f2 in instance.facilities
            ])
            objective_values[model_name] = (model.ObjVal, true_obj)
            positions[model_name] = {f:loc for loc, f in x if round(x[loc, f].X) == 1}
            runtimes[model_name] = round(model.Runtime, ndigits=2)
            if hasattr(model, '_additional_time'):
                 runtimes[model_name] += round(model._additional_time, ndigits=2)
        
        del model

    print("="*70 + "\n" + "="*70)
    print("Obj. Value:")
    for model_name, v in objective_values.items():
        status = get_model_status(statuses[model_name])
        print(f"  {model_name}: {v[1]} ({status} with {v[0]})")
    for model_name, v in statuses.items():
        if v != GRB.OPTIMAL:
            print(f"  {model_name}: {get_model_status(v)}")
    print("Runtime (s):")
    for model_name, v in runtimes.items():
        print(f"  {model_name}: {v}s")
    print("Solution:")
    for f in instance.facilities:
        line = f"{f:<{4}}: "
        for key in positions:
            p_value = positions[key].get(f, "-")
            line += f"{key:<{9}} {str(p_value):>{7}} | "
        if all([a[f] == b[f] for a,b in pairwise(positions.values())]):
            line += "✅"
        print(line)

def remove_clone_facilities(instance):
    # identify clone facilities
    isClone = set()
    equiv_classes = []
    flow_in_equiv_class = {}
    while len(isClone) < len(instance.facilities):
        unclassified_facilities = list(filterfalse(lambda x: x in isClone, instance.facilities))
        f = unclassified_facilities[0]
        equiv_class = [f]
        for g in unclassified_facilities:
            if f == g: continue
            if instance.flow[f, g] != instance.flow[g, f]: continue
            equiv = True
            for h in instance.facilities:
                if h == f or h == g: continue
                if instance.flow[f, h] != instance.flow[g, h]:
                    equiv = False
                    break
                if instance.flow[h, f] != instance.flow[h, g]:
                    equiv = False
                    break
            if equiv:
                equiv_class.append(g)
                isClone.add(g)

        if len(equiv_class) > 1:
            flow_in_equiv_class[f] = instance.flow[equiv_class[0], equiv_class[1]]
        else:
            flow_in_equiv_class[f] = 0
        equiv_classes.append(list(equiv_class))
        isClone.add(f)

    print(f"From {len(instance.facilities)} facilities to {len(equiv_classes)} Eq. Classes")

    # remove clone facilities and redefine flow matrix
    facilities = [eq[0] for eq in equiv_classes]
    equiv_class_sizes = {eq[0]:len(eq) for eq in equiv_classes}
    flow = {(f1, f2):instance.flow[f1, f2] for f1, f2 in product(facilities, repeat=2)}
    for f in facilities:
        flow[f, f] = flow_in_equiv_class[f]

    instance.clone_facilities = facilities
    instance.clone_flow = flow
    instance.equiv_class_sizes = equiv_class_sizes
    instance.equiv_classes = equiv_classes

    return len(instance.facilities) - len(equiv_classes)


# create argument parser
def create_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execute a QAP instance on different models")

    # Positional argument for the instance file path.
    parser.add_argument("instance_file",
                        help="Path to the instance python file.")

    all_models = ','.join(models.keys())
    # Optional for listing the models that shoudl be run
    parser.add_argument("-m", "--models",
                        dest="models", type=str, default=all_models,
                        help=("Comma-separated list of models you want to run."
                              f"Choose from: {all_models}"))

    # How many solutions should be generatet by gurobi
    parser.add_argument("-p", "--pool",
                        dest="pool", type=int, default=1,
                        help=("Solution Pool Size for gurobi. Make this > 1 if "
                              "you want to make sure that you have an unique optimum"))

    # merge equiv. classes ?
    parser.add_argument("-c", "--merge-clones",
                         dest="merge_clones", default=False,
                         action='store_true',
                         help=("Add flag if you want the model to merge clone "
                               "facilities in the instance"))

    # output for each indivial model ?
    parser.add_argument("--output",
                         dest="output", default=False,
                         action='store_true',
                         help=("Add flag if you want the models to print"
                               " their solution if optimal"))
    
    # Timelimiet for
    parser.add_argument("-t", "--time-limit",
                        dest="timelimit", type=int, default=-1,
                        help=("Time limit for each model in seconds. (-1 for no limit)"))


    return parser



# dynamically import modules, i.e. the instance file
def import_from_string(module_name, source_code):
    spec = util.spec_from_file_location(module_name, source_code)
    if not spec: raise Exception(f"Could not load module {module_name} in path {source_code}")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module) # pyright: ignore
    sys.modules[spec.name] = module
    return module

# from model status to string
def get_model_status(status):
    if status == GRB.OPTIMAL:
        return "OPTIMAL"
    elif status == GRB.INFEASIBLE:
        return "INFEASIBLE"
    elif status == GRB.UNBOUNDED:
        return "UNBOUNDED"
    elif status == GRB.INTERRUPTED:
        return "INTERRUPTED"
    elif status == GRB.INF_OR_UNBD:
        return "INF_OR_UNBD"
    elif status == GRB.SUBOPTIMAL:
        return "SUBOPTIMAL"
    elif status == GRB.TIME_LIMIT:
        return "TIME LIMIT reached."
    elif status == GRB.WORK_LIMIT:
        return "WORK LIMIT reached."
    elif status == GRB.ITERATION_LIMIT:
        return "ITERATION LIMIT reached."
    elif status == GRB.MEM_LIMIT:
        return "MEM LIMIT reached."
    elif status == GRB.CUTOFF:
        return "CUTOFF"    
    else:
        return f"Unknown status code: {status}"

if __name__ == '__main__':
    main()