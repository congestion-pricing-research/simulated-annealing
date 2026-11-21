import pytest
from cordon_annealing.city import City
from cordon_annealing.geometry import (is_ea_connected, is_ea_hole_free,
                                         is_ea_feasible, get_border_candidates, feasible_moves)
from cordon_annealing.objective import boundary_edge_cut


def test_connected_and_hole_free():
    city = City(5,5,1)
    graph = city.build_graph(connectivity=4)
    square = {(i,j) for i in range(1,4) for j in range(1,4)}
    assert is_ea_feasible(graph,square)
    assert is_ea_connected(graph,square - {(2,2)})
    assert not is_ea_hole_free(graph,square - {(2,2)})
    assert not is_ea_connected(graph,{(0,0),(4,4)})
    assert not is_ea_feasible(graph,set())


def test_waterfront_graph_cut():
    city = City(4,4,1)
    graph = city.build_graph(connectivity=4)
    assert boundary_edge_cut(graph,{(0,0)}) == 2
    assert boundary_edge_cut(graph,{(1,1)}) == 4
    assert boundary_edge_cut(graph,set(graph)) == 0


def test_candidates_and_valid_moves():
    graph = City(4,4,1).build_graph(connectivity=4)
    start = {(1,1),(1,2),(2,1),(2,2)}
    a,r = get_border_candidates(graph,start)
    assert (1,0) in a and (1,1) in r
    assert a == sorted(a) and r == sorted(r)
    valid_add, valid_remove = feasible_moves(graph,start)
    assert valid_add and valid_remove
    assert all(is_ea_feasible(graph, start | {x}) for x in valid_add)
    assert all(is_ea_feasible(graph, start - {x}) for x in valid_remove)
