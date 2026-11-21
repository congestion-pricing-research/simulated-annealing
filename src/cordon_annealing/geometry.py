"""Four-neighbor topology constraints for single-tile moves."""
from collections import deque
import networkx as nx


def is_ea_connected(graph, ea_set):
    """Return whether the enclosed tiles form one connected region."""
    return bool(ea_set) and nx.is_connected(graph.subgraph(ea_set))


def _is_border_node(graph, node):
    """A tile with fewer than four neighbors lies on the city boundary."""
    return graph.degree(node) < 4


def is_ea_hole_free(graph, ea_set):
    """Every complement component must connect to the filtered city's border."""
    outside = set(graph) - set(ea_set)
    if not outside:
        return True
    seeds = {node for node in outside if _is_border_node(graph, node)}
    if not seeds:
        return False
    visited = set()
    queue = deque(sorted(seeds))
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        for neighbor in graph.neighbors(node):
            if neighbor in outside and neighbor not in visited:
                queue.append(neighbor)
    return visited == outside


def is_ea_feasible(graph, ea_set):
    return is_ea_connected(graph, ea_set) and is_ea_hole_free(graph, ea_set)


def get_border_candidates(graph, ea_set):
    """Return possible additions and removals, sorted for seeded reproducibility."""
    additions, removals = set(), set()
    for node in ea_set:
        if _is_border_node(graph, node):
            removals.add(node)
        for neighbor in graph.neighbors(node):
            if neighbor not in ea_set:
                additions.add(neighbor)
                removals.add(node)
    return sorted(additions), sorted(removals)


def feasible_moves(graph, ea_set, allowed_nodes=None):
    additions, removals = get_border_candidates(graph, ea_set)
    if allowed_nodes is not None:
        additions = [node for node in additions if node in allowed_nodes]
    return (
        [n for n in additions if is_ea_feasible(graph, ea_set | {n})],
        [n for n in removals if is_ea_feasible(graph, ea_set - {n})],
    )
