import argparse
import pprint
import os
from itertools import product

def main():
    parser = create_argparser()
    args = parser.parse_args()

    facilities, locations, flow, distance = generate_instance_qaplib(args.qaplib_file, args.freelines)

    write_to_file_vars = {
        "facilities": facilities,
        "locations": locations,
        "flow": flow,
        "distance": distance,
    }
    instance_name = os.path.splitext(os.path.basename(args.qaplib_file))[0]
    filename = f"{args.folder}/{instance_name}.py" if args.folder else f"{instance_name}.py"
    save_variables_to_file(write_to_file_vars, filename)

def read_qaplib(filename, freelines):
    if not os.path.exists(filename):
        raise os.error(f"Error: File {filename} does not exsits!")
    with open(filename) as f:
        N = int(f.readline())
        freelines and f.readline()
        A = [list(map(int, f.readline().strip().split())) for _ in range(N)]
        freelines and f.readline()
        B = [list(map(int, f.readline().strip().split())) for _ in range(N)]
        return N, A, B

def generate_instance_qaplib(filename, freelines):
    N, A, B = read_qaplib(filename, freelines)

    # nodes + facilities
    facilities = [f"f{i}" for i in range(1,N+1)]
    locations = list(range(1,N+1))

    # flow + distance from matrix to dict
    flow = {}
    distance = {}
    for i, j in product(range(0, N), repeat=2):
        flow[facilities[i], facilities[j]] = A[i][j]
        distance[locations[i], locations[j]] = B[i][j]

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
    parser = argparse.ArgumentParser(description="Generate QAP instance from qaplib file")

    parser.add_argument("qaplib_file",
                        help="Path to the qaplib file")

    parser.add_argument("--no-free-lines",
                        action='store_false',
                        dest="freelines",
                        default=True,
                        help="Are there free lines between n,A,B ?")
    # store in folder
    parser.add_argument("--folder",
                        dest="folder", type=str, default="instances",
                        help=("Folder where the instance will be stored")
    )

    return parser

if __name__ == '__main__':
    main()