from cordon_annealing.city import City
from cordon_annealing.demand import from_od_rows
from cordon_annealing.objective import captured_commuters_for_ea, objective


def test_capture_and_penalty():
    city=City(3,3,1)
    city.set_protected_area(city.cell_dict.keys())
    demand=from_od_rows(city,[
        {'origin_i':0,'origin_j':0,'dest_i':1,'dest_j':1,'count':5},
        {'origin_i':1,'origin_j':1,'dest_i':1,'dest_j':1,'count':7},
        {'origin_i':2,'origin_j':2,'dest_i':0,'dest_j':0,'count':3},
    ])
    city.assign_demand_by_cell(demand)
    graph=city.build_graph(connectivity=4)
    ea={(1,1)}
    assert captured_commuters_for_ea(city,ea)==5
    assert objective(city,graph,ea,100)==5-4*100
    city.set_protected_area({(0,0)})
    assert captured_commuters_for_ea(city,ea)==0
    city.set_protected_area(city.cell_dict.keys())
    city.assign_demand_by_cell(demand)
    assert city.total_trips()==15  # reassigning does not double-count
