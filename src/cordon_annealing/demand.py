"""Origin-destination (OD) trip generation, downsampling, and CSV input."""
import csv
import random
from datetime import datetime
from pathlib import Path

from .city import Trip, TravelDemand


def from_od_rows(city, rows, *, seed=42):
    """Rows contain origin_i,origin_j,dest_i,dest_j,count; counts are integers.

    The original algorithm operates on individual trips, so counts are expanded
    into trips.
    """
    trips = []
    timestamp = datetime(2000, 1, 1)
    for row in rows:
        o = (int(row['origin_i']), int(row['origin_j']))
        d = (int(row['dest_i']), int(row['dest_j']))
        count = int(row['count'])
        if count < 0:
            raise ValueError('OD counts cannot be negative')
        if o not in city.cell_dict or d not in city.cell_dict:
            raise ValueError(f'OD endpoint outside active grid: {o} -> {d}')
        for _ in range(count):
            trip = Trip(city.cell_dict[o].centroid, city.cell_dict[d].centroid, timestamp)
            trip.origin_cell, trip.destination_cell = o, d
            trips.append(trip)
    return TravelDemand(trips)


def read_od_csv(city, path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return from_od_rows(city, csv.DictReader(handle))


def sample_demand(demand, fraction=0.5, seed=42):
    """Sample individual trips without replacement using the given seed."""
    if not 0 <= fraction <= 1:
        raise ValueError('fraction must lie in [0, 1]')
    if fraction == 0 or not demand.trips:
        return TravelDemand([])
    k = max(1, int(len(demand.trips) * fraction))
    return TravelDemand(random.Random(seed).sample(demand.trips, k))


def generate_synthetic_demand(city, *, trips_per_cell=20, hotspot_weight=5, seed=42):
    """Synthetic OD table with uniform origins, weighted hotspot destinations.

    Used for the synthetic demonstration.
    """
    if trips_per_cell < 1 or hotspot_weight < 1:
        raise ValueError('trips_per_cell and hotspot_weight must be >= 1')
    rng = random.Random(seed)
    nodes = sorted(city.cell_dict)
    hotspots = {n for n in nodes if n[0] >= .60 * city.width / city.cell_size
                and n[1] >= .60 * city.height / city.cell_size}
    if not hotspots:
        hotspots = {nodes[len(nodes)//2]}
    weights = [hotspot_weight if n in hotspots else 1 for n in nodes]
    trips = []
    for origin in nodes:
        for _ in range(trips_per_cell):
            destination = rng.choices(nodes, weights=weights, k=1)[0]
            trip = Trip(city.cell_dict[origin].centroid,
                        city.cell_dict[destination].centroid, datetime(2000, 1, 1))
            trip.origin_cell, trip.destination_cell = origin, destination
            trips.append(trip)
    return TravelDemand(trips)
