"""Functions for generating and reading initial cordon masks."""
from importlib.resources import as_file, files

import networkx as nx

from .geometry import is_ea_feasible


def rectangle(city, southwest, northeast):
    """Clip an axis-aligned rectangle to available tiles."""
    x0, y0 = southwest
    x1, y1 = northeast
    return {node for node in city.cell_dict if min(x0, x1) <= node[0] <= max(x0, x1)
            and min(y0, y1) <= node[1] <= max(y0, y1)}


def square_by_count(city, *, center, target_tiles, max_iters=30):
    """Resize a square and keep the component nearest its center."""
    if target_tiles < 1:
        raise ValueError('target_tiles must be positive')
    graph = city.build_graph(connectivity=4)
    if not graph:
        raise ValueError('Empty city')
    cx, cy = center
    ids = set(graph)
    def select(side):
        nodes = {n for n in ids if abs(n[0]-cx) <= side/2 and abs(n[1]-cy) <= side/2}
        if not nodes:
            return set()
        components = list(nx.connected_components(graph.subgraph(nodes)))
        nearest = min(nodes, key=lambda n: ((n[0]-cx)**2+(n[1]-cy)**2, n))
        return next(set(c) for c in components if nearest in c)
    lo, hi = 0.0, 2.0 * max(max(n[0] for n in ids)-min(n[0] for n in ids),
                              max(n[1] for n in ids)-min(n[1] for n in ids), 1)
    best = select(hi)
    for _ in range(max_iters):
        mid = (lo+hi)/2
        candidate = select(mid)
        if abs(len(candidate)-target_tiles) < abs(len(best)-target_tiles):
            best = candidate
        if len(candidate) < target_tiles:
            lo = mid
        else:
            hi = mid
    if not best or not is_ea_feasible(graph, best):
        raise ValueError('Could not create a feasible square; provide a starting mask')
    return best


def load_ea_csv(path):
    import csv
    with open(path, newline='', encoding='utf-8') as handle:
        return {(int(row['i']), int(row['j'])) for row in csv.DictReader(handle)}


def write_ea_csv(path, cells):
    import csv
    from pathlib import Path
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['i', 'j'])
        writer.writerows(sorted(cells))


def load_sf_start():
    """Read the bundled San Francisco starting mask."""
    resource = files("cordon_annealing").joinpath("data", "sf_start.csv")
    with as_file(resource) as path:
        return load_ea_csv(path)
