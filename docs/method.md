# Optimization method

The enclosed tiles form a connected region with no holes inside the protected area. Tiles are adjacent when they share an edge. The captured-trip count is the number of trips starting outside the cordon and ending in a protected tile inside it. The perimeter counts edges between enclosed and unenclosed city tiles. Outer edges, including edges along the waterfront, carry no perimeter cost.

An oscillation consists of an unpenalized phase of 100 iterations and a penalized phase of 300 iterations by default. The penalized phase subtracts 100,000 times the perimeter from the captured-trip count. Each step proposes either adding or removing one tile. It accepts improvements and accepts worsening moves with probability based on the change in objective and the current temperature. The temperature starts at 1, is multiplied by 0.99 each step, and resets between phases. The best state in each phase initializes the next phase. An optional hard cap applies to the starting cordon and proposed moves.

A random seed is generated for each run unless specified with `--seed`. San Francisco uses one seed for endpoint placement, sampling half the trip table, and annealing moves. The run prints its seed and records it under `config.seed` in `summary.json`. To replay a run, pass that seed with the same input exports and options.

For San Francisco, the default entry zone identifiers are 52, 17, 149, and 168. Each trip begins with an origin and destination zone. The workflow draws one point in each zone polygon and assigns each point to its nearest centroid on the full grid. It samples the trips before excluding endpoints outside the retained city.
