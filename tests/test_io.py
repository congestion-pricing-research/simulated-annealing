import json
from pathlib import Path

from cordon_annealing import cli
from cordon_annealing.initialization import load_ea_csv, load_sf_start, write_ea_csv
from cordon_annealing.demand import read_od_csv
from cordon_annealing.city import City
from cordon_annealing.annealing import AnnealingConfig, optimize
from cordon_annealing.results import save_result


def test_mask_roundtrip(tmp_path):
    cells={(2,3),(0,1)}
    write_ea_csv(tmp_path/'mask.csv',cells)
    assert load_ea_csv(tmp_path/'mask.csv')==cells


def test_bundled_sf_start():
    assert len(load_sf_start()) == 402


def test_cli_generates_a_seed_and_can_replay_it(monkeypatch, tmp_path):
    seeds = iter([0, 123])
    monkeypatch.setattr(cli, 'randbits', lambda bits: next(seeds))
    options = ['demo', '--size', '4', '--phases', '2',
               '--steps-unpenalized', '2', '--steps-penalized', '2']
    first = tmp_path / 'first'
    second = tmp_path / 'second'
    replay = tmp_path / 'replay'
    cli.main([*options, '--output', str(first)])
    cli.main([*options, '--output', str(second)])
    cli.main([*options, '--output', str(replay), '--seed', '0'])

    assert json.loads((first / 'summary.json').read_text())['config']['seed'] == 0
    assert json.loads((second / 'summary.json').read_text())['config']['seed'] == 123
    for name in ('summary.json', 'optimized_cordon.csv', 'step_history.csv'):
        assert (first / name).read_bytes() == (replay / name).read_bytes()


def test_example_od(tmp_path):
    city=City(4,4,1)
    demand=read_od_csv(city,Path(__file__).parents[1]/'data'/'example_od.csv')
    assert len(demand.trips)==59
    city.set_protected_area(city.cell_dict.keys())
    city.assign_demand_by_cell(demand)
    city.set_enclosed_area({(1,1),(1,2),(2,1),(2,2)})
    cfg=AnnealingConfig(phases=2,steps_unpenalized=3,steps_penalized=3)
    result=optimize(city,cfg)
    payload=save_result(city,result,cfg,tmp_path)
    assert payload['active_grid_tiles']==16
    for filename in ['initial_cordon.csv','optimized_cordon.csv','phase_history.csv',
                     'step_history.csv','summary.json','cordons.png','phase_history.png']:
        assert (tmp_path/filename).is_file()

    rerun = optimize(city, cfg, record_steps=False)
    save_result(city, rerun, cfg, tmp_path)
    assert not (tmp_path / 'step_history.csv').exists()
