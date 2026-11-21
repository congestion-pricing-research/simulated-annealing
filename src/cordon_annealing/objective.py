"""Trip capture and perimeter objective functions."""


def captured_commuters_for_ea(city, ea_set):
    """Trips starting outside the enclosed area and ending inside it and the protected area."""
    count = 0
    for node in ea_set:
        cell = city.cell_dict[node]
        if not cell.protected:
            continue
        for trip in cell.destination_trips:
            if trip.origin_cell not in ea_set:
                count += 1
    return count


def boundary_edge_cut(graph, ea_set):
    """Number of internal graph edges crossing the boundary; waterfront edges excluded."""
    return sum(1 for node in ea_set for other in graph.neighbors(node) if other not in ea_set)


def objective(city, graph, ea_set, perimeter_weight):
    return captured_commuters_for_ea(city, ea_set) - perimeter_weight * boundary_edge_cut(graph, ea_set)


def metrics(city, graph, ea_set):
    return {
        "captured_trips": captured_commuters_for_ea(city, ea_set),
        "enclosed_tiles": len(ea_set),
        "boundary_edges": boundary_edge_cut(graph, ea_set),
        "objective_lambda_0": objective(city, graph, ea_set, 0),
        "objective_lambda_100000": objective(city, graph, ea_set, 100000),
    }
