import argparse
import pprint
import random
import math
from itertools import product
import matplotlib.pyplot as plt

def main():
    parser = create_argparser()
    args = parser.parse_args()

    random.seed(args.seed)

    # create instance in memory
    if args.version == 1:
        facilities, locations, flow, distance = generate_instance_v1(args)
    elif args.version == 2:
        facilities, locations, flow, distance = generate_instance_v2(args)
    else:
        print(f"Unsupportet version {args.version}")
        exit()

    # save to file if `name` arg is set
    if args.name:
        write_to_file_vars = {
            "facilities": facilities,
            "locations": locations,
            "flow": flow,
            "distance": distance,
        }
        save_variables_to_file(write_to_file_vars, f"{args.name}.py")

def generate_instance_v1(args):
    N = args.size
    # create facilities and locations
    facilities = [f"f{i+1}" for i in range(N)]
    locations = list(range(1,N+1))
    if not args.quadratic:
        locations += list(range(N+1,N+random.randint(1, N//2)))

    # generate flow
    flow = {(f1, f2):random.randint(0, 50) for f1, f2 in product(facilities, repeat=2)}
    for f in facilities: flow[f, f] = 0

    # generate distance
    PLANE_MAX = 100
    coordinates = {l:(random.randint(0 ,PLANE_MAX), random.randint(0, PLANE_MAX)) for l in locations}
    distance = {}
    for l1, l2 in product(locations, repeat=2):
        dist = math.sqrt(sum((p1 - p2) ** 2 for p1, p2 in zip(coordinates[l1], coordinates[l2])))
        distance[l1, l2] = round(dist)

    # plot locations
    # x, y = zip(*coordinates.values())
    # plt.scatter(x, y)
    # plt.grid()
    # plt.show()

    return facilities, locations, flow, distance

def generate_instance_v2(args):
    N = args.size
    # create facilities and locations
    facilities = [f"f{i+1}" for i in range(N)]
    locations = list(range(1,N+1))
    if not args.quadratic:
        locations += list(range(N+1,N+random.randint(1, N//2)))

    M = len(locations)

    # generate flow
    flow = {(f1, f2):random.randint(0, 100) for f1, f2 in product(facilities, repeat=2)}
    for f in facilities: flow[f, f] = 0

    # generate distance
    ASILE_DISTANCE = 20
    coordinates = {}
    x = 0
    for i in range(0, M//2):
        coordinates[locations[i]] = (x, 0)
        #x += random.randint(1,ASILE_DISTANCE)
        x += ASILE_DISTANCE
    x = 0
    for i in range(M//2, M):
        coordinates[locations[i]] = (x, ASILE_DISTANCE)
        #x += random.randint(1,ASILE_DISTANCE)
        x += ASILE_DISTANCE

    distance = {}
    for l1, l2 in product(locations, repeat=2):
        dist = math.sqrt(sum((p1 - p2) ** 2 for p1, p2 in zip(coordinates[l1], coordinates[l2])))
        distance[l1, l2] = round(dist)

    # plot locations
    # x, y = zip(*coordinates.values())
    # plt.scatter(x, y)
    # plt.grid()
    # plt.show()

    return facilities, locations, flow, distance

def save_variables_to_file(variables, filename):
    with open(filename, 'w') as f:
        for var_name, var_value in variables.items():
            if isinstance(var_value, str):
                f.write(f'{var_name} = "{var_value}"\n')
            elif isinstance(var_value, list) or isinstance(var_value, dict):
                # Use pprint to format lists and dictionaries
                f.write(f'{var_name} = ')
                f.write(pprint.pformat(var_value, indent=4))
                f.write('\n')
            else:
                f.write(f'{var_name} = {repr(var_value)}\n')

# create argument parser
def create_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate QAP instance")

    # size of the instance
    parser.add_argument("-n", "--size",
                        dest="size", type=int, default=5,
                        help=("Size of the instance (num of facilities/location)")
    )
    # qudratic ?
    parser.add_argument("-q", "--quadratic",
                        dest="quadratic",
                        type=lambda x: x.lower() in ['true', '1', 'yes'],
                        default='True',
                        help=("Should there be the same amount of facilities as locations ?")
    )
    # name of instance - set if you want to safe it
    parser.add_argument("--name",
                        dest="name", type=str, default=None,
                        help=("Name of the instance. Only if this is set, "
                              "the instance will be written do disk as python file")
    )
    # version
    parser.add_argument("-v", "--version",
                        dest="version", type=int, default=1,
                        help=("Version of generator (1 or 2)")
    )
    # rand generator seed
    parser.add_argument("-r", "--seed",
                        dest="seed",
                        type=str,
                        default=str(random.randint(0,10000)),
                        help=("Seed for randome generator")
    )

    return parser

if __name__ == '__main__':
    main()