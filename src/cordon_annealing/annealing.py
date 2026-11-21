"""Metropolis simulated annealing with alternating perimeter penalties.

Choose an addition or removal with equal probability and fall back to the
other move type when needed. Use Metropolis acceptance for worsening moves.
Pass the best state of each phase on to the next phase.
"""
from dataclasses import dataclass, field
import math
import random

from .geometry import feasible_moves, is_ea_feasible
from .objective import boundary_edge_cut, metrics, objective


@dataclass(frozen=True)
class AnnealingConfig:
    phases: int = 80
    steps_unpenalized: int = 100
    steps_penalized: int = 300
    penalty: float = 100_000.0
    initial_temperature: float = 1.0
    cooling: float = 0.99
    normalization: float = 100.0
    minimum_temperature: float = 1e-5
    seed: int = 42
    max_boundary_edges: int | None = None

    def __post_init__(self):
        if self.phases < 1 or self.steps_unpenalized < 1 or self.steps_penalized < 1:
            raise ValueError("Phases and steps must be positive")
        if self.initial_temperature <= 0 or self.normalization <= 0:
            raise ValueError("Temperature and normalization must be positive")
        if not (0 < self.cooling <= 1):
            raise ValueError("Cooling must be in (0, 1]")
        if self.penalty < 0 or self.minimum_temperature < 0:
            raise ValueError("Penalty and minimum temperature must be nonnegative")
        if self.max_boundary_edges is not None and self.max_boundary_edges < 0:
            raise ValueError("Boundary-edge cap must be nonnegative")


@dataclass
class AnnealingResult:
    initial_ea: set
    final_ea: set
    phase_history: list[dict] = field(default_factory=list)
    step_history: list[dict] = field(default_factory=list)
    initial_metrics: dict = field(default_factory=dict)
    final_metrics: dict = field(default_factory=dict)


def optimize(city, config: AnnealingConfig, *, record_steps=True, progress=False):
    graph = city.build_graph(connectivity=4)
    allowed = {node for node, cell in city.cell_dict.items() if cell.protected}
    start = {node for node, cell in city.cell_dict.items() if cell.enclosed}
    if not start <= allowed:
        raise ValueError("Initial enclosed region must lie inside the protected area")
    if not is_ea_feasible(graph, start):
        raise ValueError("Initial enclosed region must be connected and hole-free")
    initial_metrics = metrics(city, graph, start)
    cap = config.max_boundary_edges
    if cap is not None and initial_metrics['boundary_edges'] > cap:
        raise ValueError(
            f"Initial cordon has {initial_metrics['boundary_edges']} boundary edges, "
            f"above the hard perimeter cap of {cap}"
        )
    rng = random.Random(config.seed)
    current = set(start)
    result = AnnealingResult(set(start), set(start), initial_metrics=initial_metrics)
    for phase in range(config.phases):
        penalty = 0.0 if phase % 2 == 0 else config.penalty
        n_steps = config.steps_unpenalized if phase % 2 == 0 else config.steps_penalized
        temperature = config.initial_temperature
        best = set(current)
        best_score = objective(city, graph, best, penalty)
        accepted = 0
        executed = 0
        for step in range(n_steps):
            if temperature < config.minimum_temperature:
                break
            additions, removals = feasible_moves(graph, current, allowed_nodes=allowed)
            move_type = rng.choice(('add', 'remove'))
            if move_type == 'add' and additions:
                new = current | {rng.choice(additions)}
            elif move_type == 'remove' and removals:
                new = current - {rng.choice(removals)}
            elif additions:
                new = current | {rng.choice(additions)}
            elif removals:
                new = current - {rng.choice(removals)}
            else:
                break
            if cap is not None and boundary_edge_cut(graph, new) > cap:
                accepted_move = False
                delta = float('-inf')
            else:
                delta = objective(city, graph, new, penalty) - objective(city, graph, current, penalty)
                if delta >= 0:
                    accepted_move = True
                else:
                    probability = math.exp(max(-50.0, (delta / config.normalization) / temperature))
                    accepted_move = rng.random() < probability
            if accepted_move:
                current = new
                accepted += 1
                new_score = objective(city, graph, current, penalty)
                if new_score > best_score:
                    best, best_score = set(current), new_score
            if record_steps:
                result.step_history.append({
                    'phase': phase + 1,
                    'step': step + 1,
                    'lambda': penalty,
                    'temperature': temperature,
                    'delta_objective': None if math.isinf(delta) else delta,
                    'accepted': int(accepted_move),
                    'current_captured_trips': metrics(city, graph, current)['captured_trips'],
                    'current_boundary_edges': metrics(city, graph, current)['boundary_edges'],
                    'best_objective': best_score,
                })
            temperature *= config.cooling
            executed += 1
        current = best
        phase_metrics = metrics(city, graph, current)
        result.phase_history.append({
            'phase': phase + 1, 'lambda': penalty, 'steps': executed,
            'accepted_moves': accepted, 'best_objective': best_score, **phase_metrics,
        })
        if progress:
            print(f"Phase {phase + 1}/{config.phases}: steps={executed}, "
                  f"captured={phase_metrics['captured_trips']}, "
                  f"edges={phase_metrics['boundary_edges']}", flush=True)
    city.set_enclosed_area(current)
    result.final_ea = current
    result.final_metrics = metrics(city, graph, current)
    return result
