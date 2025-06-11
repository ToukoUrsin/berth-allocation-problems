
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum, auto
from math import ceil, floor
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

import json


def _scale_and_round_down(x: int, factor: float) -> int:
    return int(floor(x / factor))


def _scale_and_round_up(x: int, factor: float) -> int:
    return int(ceil(x / factor))


class HandlingAttribute(Enum):
    FIX = auto()
    POS = auto()


class SpatialAttribute(Enum):
    DISCRETE = auto()
    HYBRID = auto()


class TemporalAttribute(Enum):
    STATIC = auto()
    DYNAMIC = auto()


class ObjectiveFunctionAttribute(Enum):
    MAX_COMPL = auto()
    SUM_WAITING_HANDLING = auto()
    WEIGHTED_SUM_WAITING_HANDLING = auto()


@dataclass
class Instance:
    path: Path
    name: str
    handling_attribute: HandlingAttribute
    spatial_attribute: SpatialAttribute
    temporal_attribute: TemporalAttribute
    objective_function_attribute: ObjectiveFunctionAttribute
    n_periods: int
    n_ships: int
    n_berths: int
    quay_len: float

    _arrival_time: Optional[List[int]] = None
    _handling_time_fix: Optional[List[int]] = None
    _handling_time_pos: Optional[Dict[Tuple[int, int], int]] = None
    _ship_len: Optional[List[float]] = None
    _berth_len: Optional[List[float]] = None
    _ship_importance: Optional[List[float]] = None


    def __init__(self, path: str | Path):
        self.path = Path(path)

        if not self.path.exists():
            raise FileNotFoundError(f"Cannot open file {self.path}")

        with self.path.open(encoding="utf-8") as fh:
            data = json.load(fh)

        self.name = self.path.stem
        self.n_periods = int(data["n_periods"])
        self.n_ships = int(data["n_ships"])
        self.n_berths = int(data["n_berths"])

        self._determine_attributes(data)

        if self.temporal_attribute is TemporalAttribute.DYNAMIC:
            self._arrival_time = list(map(int, data["arrival_time"]))

        if self.handling_attribute is HandlingAttribute.FIX:
            self._handling_time_fix = list(map(int, data["handling_time"]))
        else:
            assert self.handling_attribute is HandlingAttribute.POS

            self._handling_time_pos = {}
            ht_matrix = data["handling_time"]

            if len(ht_matrix) != self.n_ships:
                raise ValueError("handling_time outer dimension must equal n_ships")
            
            for s in range(self.n_ships):
                if len(ht_matrix[s]) != self.n_berths:
                    raise ValueError("handling_time inner dimension must equal n_berths")
                
                for b in range(self.n_berths):
                    self._handling_time_pos[(s, b)] = int(ht_matrix[s][b])

        if self.spatial_attribute is SpatialAttribute.HYBRID:
            self._ship_len = list(map(float, data["ship_len"]))
            self._berth_len = list(map(float, data["berth_len"]))

        if (self.objective_function_attribute is ObjectiveFunctionAttribute.WEIGHTED_SUM_WAITING_HANDLING):
            self._ship_importance = list(map(float, data["ship_importance"]))

        self.quay_len = sum(self._berth_len) if self._berth_len is not None else float(self.n_berths)

    def _determine_attributes(self, data: Mapping):
        self.temporal_attribute = TemporalAttribute.DYNAMIC if "arrival_time" in data else TemporalAttribute.STATIC

        if ("ship_len" in data) + ("berth_len" in data) == 1:
            raise ValueError("An instance either has both ship_len and berth_len or none of them.")

        self.spatial_attribute = SpatialAttribute.HYBRID if "ship_len" in data and "berth_len" in data else SpatialAttribute.DISCRETE

        if not data.get("handling_time"):
            raise ValueError(f"Instance {self.path.name} lacks required 'handling_time' field")
        
        first_ht = data["handling_time"][0]
        if isinstance(first_ht, (int, float)):
            self.handling_attribute = HandlingAttribute.FIX
        elif isinstance(first_ht, list):
            self.handling_attribute = HandlingAttribute.POS
        else:
            raise ValueError("Unsupported format for 'handling_time' field")

        obj_str = data.get("objective_function")
        if obj_str == "MaxCompl":
            self.objective_function_attribute = ObjectiveFunctionAttribute.MAX_COMPL
        elif obj_str == "SumWaitingHandling":
            self.objective_function_attribute = ObjectiveFunctionAttribute.SUM_WAITING_HANDLING
        elif obj_str == "WeightedSumWaitingHandling":
            self.objective_function_attribute = ObjectiveFunctionAttribute.WEIGHTED_SUM_WAITING_HANDLING
        else:
            if "ship_importance" in data:
                self.objective_function_attribute = ObjectiveFunctionAttribute.WEIGHTED_SUM_WAITING_HANDLING
            else:
                self.objective_function_attribute = ObjectiveFunctionAttribute.MAX_COMPL

    def arrival_time(self, ship: int) -> int:
        if self.temporal_attribute is not TemporalAttribute.DYNAMIC:
            raise RuntimeError("arrival_time available only for dynamic instances")
        
        if ship < 0 or ship > self.n_ships - 1:
            raise IndexError(f"Index {ship} invalid for an instance with {self.n_ships} ships")
        
        return self._arrival_time[ship]  # type: ignore[arg-type]

    def handling_time(self, ship: int, berth: int | None = None) -> int:
        """
        Overloaded behaviour:
            • handling_time(ship)          # FIX handling
            • handling_time(ship, berth)   # POS handling
        """
        if ship < 0 or ship > self.n_ships - 1:
                raise IndexError(f"Index {ship} invalid for an instance with {self.n_ships} ships")
        
        if berth is not None and (berth < 0 or berth > self.n_berths - 1):
            raise IndexError(f"Index {berth} invalid for an instance with {self.n_berths} berths")

        if self.handling_attribute is HandlingAttribute.FIX:
            if berth is not None:
                raise RuntimeError("Berth index invalid for FIX handling attribute")

            return self._handling_time_fix[ship]  # type: ignore[arg-type]

        if berth is None:
            raise RuntimeError("Berth index required for POS handling attribute")
        
        return self._handling_time_pos[(ship, berth)]  # type: ignore[index]

    def ship_len(self, ship: int) -> float:
        if self.spatial_attribute is not SpatialAttribute.HYBRID:
            raise RuntimeError("Ship length available only for HYBRID spatial models")
        
        return self._ship_len[ship]  # type: ignore[arg-type]

    def berth_len(self, berth: int) -> float:
        if self.spatial_attribute is not SpatialAttribute.HYBRID:
            raise RuntimeError("Berth length available only for HYBRID spatial instances")
        
        return self._berth_len[berth]  # type: ignore[arg-type]
    
    def berth_start(self, berth: int) -> float:
        if self.spatial_attribute is not SpatialAttribute.HYBRID:
            raise RuntimeError("Berth start available only for HYBRID spatial instances")
        
        if berth == 0:
            return 0.0

        return sum(self._berth_len[:berth-1]) # type: ignore[arg-type]

    def ship_importance(self, ship: int) -> float:
        if self.objective_function_attribute is not ObjectiveFunctionAttribute.WEIGHTED_SUM_WAITING_HANDLING:
            raise RuntimeError("Ship importance available only for weighted objective instances")
        return self._ship_importance[ship]  # type: ignore[arg-type]

    def ships(self):
        return range(self.n_ships)

    def periods(self):
        return range(self.n_periods)

    def berths(self):
        return range(self.n_berths)

    def rescale_conservative(self, factor: float) -> "Instance":
        new = deepcopy(self)
        new.n_periods = _scale_and_round_down(new.n_periods, factor)

        if new.temporal_attribute is TemporalAttribute.DYNAMIC:
            new._arrival_time = [_scale_and_round_up(a, factor) for a in new._arrival_time]

        if new.handling_attribute is HandlingAttribute.FIX:
            new._handling_time_fix = [_scale_and_round_up(h, factor) for h in new._handling_time_fix]
        else:
            new._handling_time_pos = {
                k: _scale_and_round_up(v, factor)
                for k, v in new._handling_time_pos.items()
            }

        return new

    def rescale_aggressive(self, factor: float) -> "Instance":
        new = deepcopy(self)
        new.n_periods = _scale_and_round_up(new.n_periods, factor)

        if new.temporal_attribute is TemporalAttribute.DYNAMIC:
            new._arrival_time = [_scale_and_round_down(a, factor) for a in new._arrival_time]

        if new.handling_attribute is HandlingAttribute.FIX:
            new._handling_time_fix = [_scale_and_round_down(h, factor) for h in new._handling_time_fix]
        else:
            new._handling_time_pos = {
                k: _scale_and_round_down(v, factor)
                for k, v in new._handling_time_pos.items()
            }

        return new
