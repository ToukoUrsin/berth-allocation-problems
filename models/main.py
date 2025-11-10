import argparse
import sys
sys.path.append('../src/python')

from instance import Instance
from bap.pa_solver import PASolver
from bap.rp_solver import RPSolver
from bap.s_solver import SSolver
from bap.ti_solver import TISolver
from bap.gspp_solver import GSPPSolver

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='main',
        description='Main solver programme for multiple BAP models'
    )

    parser.add_argument(
        '-i', '--instance', action='store', help='Path to the instance file')
    parser.add_argument(
        '-m', '--model', action='store', help='Model to use',
        choices=('pa', 'rp', 's', 'ti', 'gspp'))
    parser.add_argument(
        '-s', '--starting-solution', action='store', type=str,
        help='File containing a starting solution')
    parser.add_argument(
        '-f', '--fix-starting', action='store_true',
        help='If the flag is given, the starting solution is fixed rather than used as a hint')
    parser.add_argument(
        '-z', '--compute-iis', action='store_true',
        help='If the flag is given and the model is unfeasible, compute the IIS')
    parser.add_argument(
        '-o', '--output-folder', action='store', type=str,
        help='Output folder', default='results')
    
    args = parser.parse_args()
    
    i = Instance(path=args.instance)

    if args.model == 'pa':
        m = PASolver(instance=i, output_folder=args.output_folder)
    elif args.model == 'rp':
        m = RPSolver(instance=i, output_folder=args.output_folder)
    elif args.model == 's':
        m = SSolver(instance=i, output_folder=args.output_folder)
    elif args.model == 'ti':
        m = TISolver(instance=i, output_folder=args.output_folder)
    elif args.model == 'gspp':
        m = GSPPSolver(instance=i, output_folder=args.output_folder)
    else:
        raise NotImplementedError(f"Model {args.model} not recognised")
    
    if args.starting_solution is not None:
        fix = (args.fix_starting is not None) and args.fix_starting
        print(f"Using a starting solution. Fix = {fix}.")
        m.load_initial(initial_file=args.starting_solution, fix=fix)
    
    m.solve(compute_iis=args.compute_iis)
