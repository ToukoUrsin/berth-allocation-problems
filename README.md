## Instances, Best Known Solutions and Models for Berth Allocation Problems

This repository contains instances, solutions, and models for Berth Allocation Problems.
At the present moment, it contains data for a single problem with the following characteristics:

* Temporal aspect: dynamic (not all ships are available at the beginning of the time horizon).
* Spatial aspect: hybrid (some ship occupies more than one berth).
* Handling aspect: fixed (the ship handling time depends on the ship but not on the assigned berth).
* Objective function: minimising the total completion time.

This variant of the problem is denoted as `hyb|dyn|fix|max(comp)` in the notation introuced in: Bierwirth, Christian and Frank Meisel (2015). “A follow-up survey of berth allocation and quay crane scheduling problems in container terminals”. In: European Journal of Operational Research 244, pp. 675–689.

### Instances

The instances were created starting from data made available by the [Port of Barcelona](https://opendata.portdebarcelona.cat/), Spain.
We used data relative to quays 24B (APM Terminals) and 36A (Barcelona Europe South Terminal) and describing container ship movements during 2024.
Instances are in folder `instances/hyb_dyn_fix_max-comp`.
The file name is `bcn_<quay>_<startweek>.json`, where `<quay>` is either 24B or 36A and `<startweek>` refers to the first week of the year 2024 included in the data.
To avoid inconsistencies with ships starting service in 2023 and ending it in 2024 or starting in 2024 and ending in 2025, we do not use the first and last week of the year and `<startweek>` goes from 2 to 50.

#### Instance format

The instances are in Json format, with the following structure:

* `n_ships`: number of ships arriving over the time horizon.
* `n_berths`: number of available berths.
* `n_periods`: number of periods in the time horizon. Solvers might not use this information. It is expressed in the same unit of measure as the arrival and handling times.
* `berth_len`: an array with one entry per berth. It is the berth length, expressed in the same unit of measure as the ship length (see below).
* `arrival_time`: an array with one entry per ship. It is the ship arrival time, expressed in the same unit of measure as the time horizon length (see above) and the handling times (see below).
* `handling_time`: an array with one entry per ship. It is the ship handling time, i.e., the time necessary for loading and unloading operations. It is expressed in the same unit of measure as the time horizon length and the arrival time (see above).
* `ship_len`: an array with one entry per ship. It is the ship length, expressed in the same unit of measure as the berth length (see above).

This format can be extended for other Berth Allocation Problems.

* Attribute `handling_time` can be turned into a two-dimensional array indexed by ship and berth, containing the ship's handling time when mooring with the leftmost end at the given berth.
* One can use an additional attribute `ship_importance` if ships should have different priorities when it comes to berthing.

#### Instance generator

The instance generator and the input files used to create the instances are in folder `generator`.
They can be used to create different instance sets startgin from the 2024 Port of Barcelona data.

### Best known solutions

Best known solutions (BKS) are available in folder `bks`.
They are currently only available for the `hyb|dyn|fix|max(comp)` problem type.
There is one BKS for each instance, in Json format, with the following structure:

* `solver`: comma-separated list of solvers that found the given best known primal feasible solution within a one-hour time limit. Valid values are "s", "ti", "rp", "pa", "gspp", which indicate five formulations [described below](#models), and "sgcp", indicating a search procedure that uses the [Selective Graph Colouring Problem](https://github.com/alberto-santini/selective-graph-colouring) and dynamic time discretisation. This search procedure is described in a [recent preprint](https://santini.in/files/papers/santini-2026.pdf).
* `makespan`: makespan of the best known primal feasible solution. If the instance was not solved to optimality, this is a strict upper bound on the optimal solution value.
* `dual_bound`: tightest known dual bound for the objective value of the instance.
* `ships`: list describing when and where ships berth in the given primal feasible solution. Each element of the list contains some fields starting with `data_`. This is data that can be find directly in the instance file (ship id, ship length, arrival time, handling time) and does not influence the solution. By contrast, the `mooring_time` and `mooring_berth` fields describe in which period and at which berth the leftmost end of the ship berthed. They constitute the main information provided in the solution.

New BKS can be submitted in the same format by [contacting the author](mailto:alberto.santini@upf.edu).

### Utilities

We provide code to read the instances for both `C++` and `Python`, respectively in folders `src/cpp` and `src/python`.
You can use this code in your repository to jump straight to the algorithm development phase, without worring about the "boring" data reading part.
For example, the following C++ code reads an instance.

```cpp
#include "Instance.h"

int main() {
    using namespace bap;
    const auto instance = Instance{"/path/to/bcn_36A_6.json"};

    for(auto&& ship : instance.ships()) {
        std::cout << "Length: " << instance.ship_len(ship) << "\n";
    }

    return 0;
}
```

```python
from instance import Instance


if __name__ == '__main__':
    inst = Instance(path="/path/to/bcn_36A_6.json")

    for ship in inst.ships():
        print(f"Length: {inst.ship_len(ship)}")
```

### Models

Solvers for five formulations are in folder `models/bap`.
They are implemented in Python using Gurobi.
The five implemented models are:

* The *Relative Position* and *Position Assignment* formulations presented in the following paper: Y. Guan and R. K. Cheung, "The berth allocation problem: models and solution methods", OR Spectrum, vol. 26, pp. 75–92, 2004.
* The *Sequence-variables* and *Time Index* formulations presented in the following paper: A. Ernst, C. Oguz, G. Singh, and G. Taherkhani, "Mathematical models for the berth allocation problem in dry bulk terminals", Journal of Scheduling, vol. 20, pp. 459–473, 2017.
* The *Generalised Set Partitioning Problem* formulation presented in the following thesis: C. G. Christensen and Holst C. T., "Allokering af kajplads i containerhavne", Thesis number Imm-m.sc.-2008-37, MA thesis, Danish Technical University, 2018.

### Citation

You can cite this repository via Zenodo:

```bib
@misc{bap_github,
    title={Instances, Best Known Solutions and Models for Berth Allocation Problems},
    author={Santini, Alberto},
    date={2025-11-20},
    howpublished={Github repository},
    doi={???},
    url={https://github.com/alberto-santini/berth-allocation-problems/}
}
```

### License

The code in folders `generator`, `models` and `src` is provided under the GNU General Public License v3.
See the `LICENSE` file.
