import pytest
from cordon_annealing import City, AnnealingConfig, optimize
from cordon_annealing.cli import build_parser
from cordon_annealing.demand import generate_synthetic_demand, sample_demand
from cordon_annealing.geometry import is_ea_feasible
from cordon_annealing.initialization import square_by_count
from cordon_annealing.objective import captured_commuters_for_ea


def make_city():
    city=City(5,5,1)
    city.set_protected_area(city.cell_dict)
    demand=generate_synthetic_demand(city,trips_per_cell=5,seed=7)
    city.assign_demand_by_cell(demand)
    city.set_enclosed_area(square_by_count(city,center=(2,2),target_tiles=9))
    return city


def test_seed_reproducible():
    cfg=AnnealingConfig(phases=4,steps_unpenalized=5,steps_penalized=6,seed=31)
    result1=optimize(make_city(),cfg)
    result2=optimize(make_city(),cfg)
    assert result1.final_ea==result2.final_ea
    assert result1.phase_history==result2.phase_history
    assert result1.step_history==result2.step_history
    assert len(result1.phase_history)==4
    assert [p['lambda'] for p in result1.phase_history]==[0,100000,0,100000]
    graph=make_city().build_graph(connectivity=4)
    assert is_ea_feasible(graph,result1.final_ea)


def test_protected_region_restriction():
    city=make_city()
    city.set_protected_area({(2,2)})
    with pytest.raises(ValueError,match='protected area'):
        optimize(city,AnnealingConfig(phases=1,steps_unpenalized=2))


def test_optional_hard_cap():
    city=make_city()
    cfg=AnnealingConfig(phases=2,steps_unpenalized=3,steps_penalized=3,max_boundary_edges=12)
    result=optimize(city,cfg)
    assert result.final_metrics['boundary_edges']<=12


def test_hard_cap_rejects_over_limit_start():
    city = make_city()
    cfg = AnnealingConfig(phases=1, steps_unpenalized=1, max_boundary_edges=11)
    with pytest.raises(ValueError, match="Initial cordon has 12 boundary edges"):
        optimize(city, cfg)


def test_default_schedule_runs_forty_oscillations():
    args = build_parser().parse_args(['sf'])
    assert (args.phases, args.steps_unpenalized, args.steps_penalized) == (80, 100, 300)
    assert args.largest_component
    assert args.expected_tiles == 804
    assert args.taz_file.as_posix() == 'input/sf/transportation_analysis_zones_1454.shp'
    assert args.trip_file.as_posix() == 'input/sf/indivTripData_3.csv'
    cfg = AnnealingConfig(steps_unpenalized=1, steps_penalized=2)
    result = optimize(make_city(), cfg, record_steps=False)
    phases = [(phase['lambda'], phase['steps']) for phase in result.phase_history]
    assert phases == [(0, 1), (100_000, 2)] * 40


def test_sampling_seed_and_length():
    demand=generate_synthetic_demand(make_city(),trips_per_cell=4,seed=3)
    a=sample_demand(demand,fraction=.5,seed=5)
    b=sample_demand(demand,fraction=.5,seed=5)
    assert len(a.trips)==len(demand.trips)//2
    assert [id(t) for t in a.trips]==[id(t) for t in b.trips]
