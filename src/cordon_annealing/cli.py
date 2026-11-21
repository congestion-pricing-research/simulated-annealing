"""Console entry point for synthetic and San Francisco experiments."""
import argparse
import json
from pathlib import Path
from secrets import randbits

from .annealing import AnnealingConfig, optimize
from .city import City
from .demand import generate_synthetic_demand, read_od_csv
from .geometry import is_ea_feasible
from .initialization import load_ea_csv, load_sf_start, square_by_count
from .objective import boundary_edge_cut
from .results import save_result


def build_parser():
    parser = argparse.ArgumentParser(prog='cordon-annealing', description='Single-cordon simulated annealing')
    sub = parser.add_subparsers(dest='command', required=True)
    defaults = AnnealingConfig()
    for name in ('demo', 'sf'):
        cmd = sub.add_parser(name, help='Synthetic demonstration' if name == 'demo' else 'San Francisco experiment')
        cmd.add_argument('--output', type=Path, default=Path('output') / name)
        cmd.add_argument('--seed', type=int, help='Random seed for replaying a run. Omit to generate a fresh seed.')
        cmd.add_argument('--phases', type=int, default=defaults.phases)
        cmd.add_argument('--steps-unpenalized', type=int, default=defaults.steps_unpenalized)
        cmd.add_argument('--steps-penalized', type=int, default=defaults.steps_penalized)
        cmd.add_argument('--penalty', type=float, default=defaults.penalty)
        cmd.add_argument('--cooling', type=float, default=defaults.cooling)
        cmd.add_argument('--normalization', type=float, default=defaults.normalization)
        cmd.add_argument('--hard-perimeter-cap', type=int, default=None)
        cmd.add_argument('--initial-ea', type=Path, help='Optional CSV with i,j tile identifiers')
        cmd.add_argument('--square-center', type=float, nargs=2, default=None, metavar=('I','J'))
        cmd.add_argument('--square-count', type=int, default=None)
        cmd.add_argument('--no-step-history', action='store_true')
    demo = sub.choices['demo']
    demo.add_argument('--size', type=int, default=10)
    demo.add_argument('--trips-per-cell', type=int, default=15)
    demo.add_argument('--od-csv', type=Path, help='Use explicit cell-level OD CSV instead of synthetic trips')
    sf = sub.choices['sf']
    sf.add_argument(
        '--taz-file', type=Path, default=Path('input/sf/transportation_analysis_zones_1454.shp'),
        help='Transportation analysis zone shapefile in input/sf by default',
    )
    sf.add_argument(
        '--trip-file', type=Path, default=Path('input/sf/indivTripData_3.csv'),
        help='Individual trip table in input/sf by default',
    )
    sf.add_argument('--fraction', type=float, default=0.5)
    sf.add_argument('--expected-tiles', type=int, default=804, help='Expected retained tiles, or 0 to skip the check')
    sf.add_argument(
        '--largest-component', action=argparse.BooleanOptionalAction, default=True,
        help='Keep the largest group of edge-connected tiles',
    )
    sf.add_argument('--entry-taz-ids', nargs='+', type=int, default=[52, 17, 149, 168])
    return parser


def run(args):
    seed = args.seed if args.seed is not None else randbits(32)
    print(f'Seed: {seed}', flush=True)
    if args.command == 'demo':
        city = City(args.size, args.size, 1)
        city.set_protected_area(city.cell_dict.keys())
        if args.od_csv:
            demand = read_od_csv(city, args.od_csv)
        else:
            demand = generate_synthetic_demand(city, trips_per_cell=args.trips_per_cell, seed=seed)
        city.assign_demand_by_cell(demand)
        default_count = max(1, args.size * args.size // 4)
        default_center = ((args.size - 1) / 2, (args.size - 1) / 2)
    else:
        from .geography import load_mtc_case

        for path, flag in ((args.taz_file, '--taz-file'), (args.trip_file, '--trip-file')):
            if not path.is_file():
                raise FileNotFoundError(f'Input file not found: {path}. See the README or set {flag}.')
        city, demand, _ = load_mtc_case(
            args.taz_file, args.trip_file, fraction=args.fraction,
            seed=seed, expected_tiles=args.expected_tiles or None,
            largest_component=args.largest_component, entry_taz_ids=args.entry_taz_ids)
        default_count = 402
        default_center = (city.width * .95, city.height * .15)
    bundled_start = (
        args.command == 'sf' and args.initial_ea is None
        and args.square_center is None and args.square_count is None
    )
    if args.initial_ea:
        start = load_ea_csv(args.initial_ea)
    elif bundled_start:
        start = load_sf_start()
    else:
        center = args.square_center if args.square_center is not None else default_center
        count = args.square_count if args.square_count is not None else default_count
        start = square_by_count(city, center=center, target_tiles=count)
    if not start <= city.cell_dict.keys():
        raise ValueError('Initial mask references cells removed by geographic filtering')
    city.set_enclosed_area(start)
    graph = city.build_graph(connectivity=4)
    if not is_ea_feasible(graph, start):
        raise ValueError('Initial cordon is not connected and hole-free')
    if bundled_start and (len(start), boundary_edge_cut(graph, start)) != (402, 46):
        raise ValueError('The bundled start requires 402 enclosed tiles and 46 boundary edges. Verify the zone geometry.')
    cfg = AnnealingConfig(
        seed=seed, phases=args.phases, steps_unpenalized=args.steps_unpenalized,
        steps_penalized=args.steps_penalized, penalty=args.penalty,
        cooling=args.cooling, normalization=args.normalization,
        max_boundary_edges=args.hard_perimeter_cap,
    )
    print(f'Active tiles: {len(city.cells)} | Trips: {len(demand.trips)} | Initial tiles: {len(start)}')
    result = optimize(city, cfg, record_steps=not args.no_step_history, progress=True)
    payload = save_result(city, result, cfg, args.output, label=args.command)
    print(json.dumps({'initial': payload['initial'], 'final': payload['final']}, indent=2))
    print(f'Outputs: {args.output.resolve()}')
    return payload


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        run(args)
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
