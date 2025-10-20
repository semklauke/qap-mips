#!/usr/bin/env python3

import argparse, os, sys
import pkgutil
from importlib import util, import_module
from itertools import pairwise

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

    ##### solve
    objective_values = {}
    positions = {}
    runtimes = {}


    for model_name in models_to_run:
        model, x = models[model_name].solve(
            instance.facilities,
            instance.locations,
            instance.distance,
            instance.flow,
            False,
            args.pool
        )

        if model.Status != GRB.OPTIMAL:
            print(f"{model_name} model not optimal.")
        else:
            true_obj = sum([
                instance.flow[f1, f2] *
                instance.distance[loc1, loc2] *
                round(x[loc1, f1].X) *
                round(x[loc2, f2].X)
                for (loc1, f1) in x.keys() for (loc2, f2) in x.keys()
            ])
            objective_values[model_name] = (model.ObjVal, true_obj)
            positions[model_name] = {f:loc for loc, f in x if round(x[loc, f].X) == 1}
            runtimes[model_name] = round(model.Runtime, ndigits=2)
            if hasattr(model, '_additional_time'):
                 runtimes[model_name] += round(model._additional_time, ndigits=2)


    print("="*50)
    print("Obj. Value:")
    for model_name, v in objective_values.items():
        print(f"  {model_name}: {v[1]} ({v[0]})")
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
                        help=("Solution Pool Size for gurobi. Make this > 1 if you want to"
                              " make sure that you have an unique optimum"))
    return parser

# dynamically import modules, i.e. the instance file
def import_from_string(module_name, source_code):
    spec = util.spec_from_file_location(module_name, source_code)
    if not spec: raise Exception(f"Could not load module {module_name} in path {source_code}")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module) # pyright: ignore
    sys.modules[spec.name] = module
    return module

if __name__ == '__main__':
    main()