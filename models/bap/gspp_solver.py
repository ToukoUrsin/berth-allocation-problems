from instance import Instance
from typing import Union, List, Dict, Tuple
from gurobipy import Model, tupledict, Var, GRB
from os import path
from datetime import datetime
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
import json


class GSPPSolver:
    instance: Instance
    output_folder: str
    grb_timelimit: float

    vbap: List[Tuple[int, int, int]]

    m: Model
    x: tupledict
    makespan: Var

    start_ti: datetime

    def __init__(self, instance: Union[str, Instance], output_folder: str, **kwargs):
        if type(instance) is Instance:
            self.instance = instance
        elif type(instance) is str:
            self.instance = Instance(path=instance)
        else:
            raise TypeError(f"Type not supported for instance: {type(instance)}")
        
        self.output_folder = output_folder
        
        self.start_ti = datetime.now()
        self.__build_model()

        self.grb_timelimit = kwargs.get('grb_timelimit', 3600.0)

    def __build_model(self) -> None:
        time = list(range(self.instance.n_periods))
        self.vbap = [
            (i, j, t)
            for i in self.instance.ships()
            for j in range(self.instance.n_berths - int(self.instance.ship_len(i)))
            for t in range(self.instance.arrival_time(i), self.instance.n_periods - self.instance.handling_time(i) + 2)
        ]

        self.m = Model()
        self.x = self.m.addVars(self.vbap, vtype=GRB.BINARY)
        self.makespan = self.m.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=GRB.INFINITY, obj=1)

        self.m.addConstrs(
            self.makespan >= (t + self.instance.handling_time(i) - 1) * self.x[i, j, t] for i, j, t in self.vbap
        )

        self.m.addConstrs(
            self.x.sum(i, '*', '*') == 1 for i in self.instance.ships()
        )

        self.m.addConstrs(
            sum(
                self.x[i, jj, tt]
                for (i, jj, tt) in self.vbap
                if  jj <= j <= jj + int(self.instance.ship_len(i)) and
                    tt <= t <= tt + self.instance.handling_time(i)
            ) <= 1
            for j in self.instance.berths()
            for t in time
        )

    def load_initial(self, initial_file: str, fix: bool = False) -> None:
        with open(initial_file) as f:
            init = json.load(f)

        for data in init['ships']:
            i = data['data_ship_id']
            j = data['mooring_position']
            t = data['mooring_time']

            if (i,j,t) in self.vbap:
                if fix:
                    self.x[i,j,t].LB = self.x[i,j,t].UB = 1
                else:
                    self.x[i,j,t].Start = 1

    def solve(self, compute_iis: bool = False) -> None:
        basename = path.splitext(path.basename(self.instance.path))[0]
        self.m.setParam(GRB.Param.TimeLimit, self.grb_timelimit)
        self.m.setParam(GRB.Param.Threads, 1)
        self.m.optimize()

        end_ti = datetime.now()
        elapsed_time = (end_ti - self.start_ti).total_seconds()

        if self.m.SolCount > 0:
            results = dict(
                feasible=True,
                makespan=self.m.ObjVal,
                dual_bound=self.m.ObjBound,
                solve_time=self.m.Runtime,
                total_time=elapsed_time,
                ships=list()
            )

            for i, j, t in self.vbap:
                if self.x[i,j,t].X > 0.5:
                    results['ships'].append(dict(
                        data_ship_id=i,
                        data_arrival_time=self.instance.arrival_time(i),
                        data_handling_time=self.instance.handling_time(i),
                        data_ship_length=self.instance.ship_len(i),
                        mooring_time=t,
                        completion_time=t + self.instance.handling_time(i) - 1,
                        mooring_berth=j
                    ))
        elif self.m.Status != GRB.INFEASIBLE:
            results = dict(
                feasible=True,
                makespan=None,
                dual_bound=self.m.ObjBound,
                solve_time=self.m.Runtime,
                total_time=elapsed_time,
                ships=None
            )
        else:
            print('Infeasible model (GSPP)')

            if compute_iis:
                self.m.computeIIS()
                model_file = 'infeas-' + basename + '-gsppmodel.lp'
                ilp_file = 'infeas-' + basename + '-gsppiis.ilp'

                self.m.write(model_file)
                self.m.write(ilp_file)

                print(f"Infeasible model. Model written to {model_file}. IIS written to {ilp_file}.")
            
            results = dict(
                feasible=False,
                makespan=None,
                dual_bound=None,
                solve_time=self.m.Runtime,
                total_time=elapsed_time,
                ships=None
            )

        results_file = self.output_folder + '/results-' + basename + '-gsppsolver.json'

        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
