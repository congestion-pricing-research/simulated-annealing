"""Build the San Francisco grid and map zone-level trip records to tiles."""
from datetime import datetime

import numpy as np
import geopandas as gpd
import networkx as nx
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import Point

from .city import City, Trip, TravelDemand


def _build_sf_grid(taz_gdf, grid_size, cell_size, retain_largest_component):
    sf = taz_gdf[taz_gdf['county'].astype(str).str.lower() == 'san francisco'].copy()
    if sf.empty:
        raise ValueError('No San Francisco zones found (county column)')
    city = City(grid_size, grid_size, cell_size)
    cell_to_latlon, _ = map_cells_and_taz_by_bbox(city, sf)
    filter_city_to_taz_area(city, cell_to_latlon, sf)
    if retain_largest_component:
        filter_city_to_largest_component(city, connectivity=4)
    return city, sf, cell_to_latlon


def build_sf_grid(taz_gdf, *, grid_size=200, cell_size=1, retain_largest_component=True):
    """Return the city, its zones, and the coordinates of its retained tiles."""
    city, sf, centroids = _build_sf_grid(
        taz_gdf, grid_size, cell_size, retain_largest_component
    )
    return city, sf, {tile: centroids[tile] for tile in city.cell_dict}


def map_cells_and_taz_by_bbox(city, destination_gdf):
    """Fit a square grid to the San Francisco zone bounding box."""
    wgs = destination_gdf.to_crs('EPSG:4326')
    west, south, east, north = wgs.total_bounds
    lat_extent, lon_extent = north - south, east - west
    if lat_extent >= lon_extent:
        scale = lat_extent / city.height
    else:
        scale = lon_extent / city.width
    ids = [cell.id for cell in city.cells]
    coords = [(south + cell.centroid[1] * scale, west + cell.centroid[0] * scale)
              for cell in city.cells]
    cell_to_latlon = dict(zip(ids, coords))
    projected = destination_gdf.to_crs('EPSG:3310')
    centroids_ll = projected.geometry.centroid.to_crs('EPSG:4326')
    taz_latlon = np.column_stack([centroids_ll.y.to_numpy(), centroids_ll.x.to_numpy()])
    tree = cKDTree(np.asarray(coords))
    _, indices = tree.query(taz_latlon)
    taz_to_cell = {taz_id: ids[int(i)] for taz_id, i in zip(destination_gdf['taz1454'], indices)}
    return cell_to_latlon, taz_to_cell


def filter_city_to_taz_area(city, cell_to_latlon, taz_gdf):
    """Keep tiles whose mapped centroids fall inside the city zones."""
    points = gpd.GeoDataFrame({'cell_id': [c.id for c in city.cells]},
                              geometry=[Point(cell_to_latlon[c.id][1], cell_to_latlon[c.id][0])
                                        for c in city.cells], crs='EPSG:4326')
    if points.crs != taz_gdf.crs:
        points = points.to_crs(taz_gdf.crs)
    joined = gpd.sjoin(points, taz_gdf, how='inner', predicate='within')
    valid_ids = set(joined['cell_id'])
    city.cells = [c for c in city.cells if c.id in valid_ids]
    city.cell_dict = {c.id: c for c in city.cells}
    if not city.cells:
        raise ValueError('SF mask yielded no grid cells')
    return city


def filter_city_to_largest_component(city, connectivity=4):
    """Keep the largest group of tiles connected by the requested adjacency."""
    graph = city.build_graph(connectivity=connectivity)
    keep_ids = set(max(nx.connected_components(graph), key=len))
    city.cells = [c for c in city.cells if c.id in keep_ids]
    city.cell_dict = {c.id: c for c in city.cells}
    return keep_ids


def reroute_outside_origins_to_entry_taz(trips_df, sf_gdf, all_taz_gdf, entry_taz_ids):
    """Map outside origins to the nearest of the specified entry zones."""
    result = trips_df.copy()
    mask = ~result['orig_taz'].isin(sf_gdf['taz1454'])
    orig_ids = set(result.loc[mask, 'orig_taz'])
    external = all_taz_gdf[all_taz_gdf['taz1454'].isin(orig_ids)].to_crs('EPSG:3310')
    entries = all_taz_gdf[all_taz_gdf['taz1454'].isin(entry_taz_ids)].to_crs('EPSG:3310')
    if mask.any() and entries.empty:
        raise ValueError('No entry zone IDs found in zone file')
    mapping = {}
    for _, origin_row in external.iterrows():
        distances = entries.geometry.centroid.distance(origin_row.geometry.centroid)
        mapping[origin_row['taz1454']] = entries.loc[distances.idxmin(), 'taz1454']
    result.loc[mask, 'orig_taz'] = result.loc[mask, 'orig_taz'].map(mapping)
    if result[['orig_taz', 'dest_taz']].isna().any().any():
        raise ValueError('An external origin could not be assigned to an entry TAZ')
    return result


def _latlon_to_unit_xyz(lat_deg, lon_deg):
    lat = np.deg2rad(lat_deg)
    lon = np.deg2rad(lon_deg)
    cos = np.cos(lat)
    return np.column_stack((cos * np.cos(lon), cos * np.sin(lon), np.sin(lat)))


def generate_synthetic_demand_from_trip_list_simple(
        city, trips_df, taz_gdf, cell_to_latlon, *, taz_id_col='taz1454', seed=42, progress=True):
    """Sample endpoints within their zones and map to the supplied centroids."""
    from tqdm.auto import tqdm
    rng = np.random.default_rng(seed)
    gdf = taz_gdf.to_crs('EPSG:4326')
    lookup = dict(zip(gdf[taz_id_col].astype(int), gdf.geometry))
    ids = sorted(cell_to_latlon)
    latlons = np.asarray([cell_to_latlon[node] for node in ids])
    tree = cKDTree(_latlon_to_unit_xyz(latlons[:, 0], latlons[:, 1]))

    def sample_point(polygon):
        west, south, east, north = polygon.bounds
        for _ in range(200):
            point = Point(rng.uniform(west, east), rng.uniform(south, north))
            if polygon.covers(point):
                return point
        return polygon.representative_point()

    trips = []
    rows = tqdm(trips_df.itertuples(index=False), total=len(trips_df),
                desc='Map trips to full grid', disable=not progress)
    for row in rows:
        o_id, d_id = int(row.orig_taz), int(row.dest_taz)
        if o_id not in lookup or d_id not in lookup:
            raise KeyError(f'Missing TAZ geometry: {o_id} or {d_id}')
        op = sample_point(lookup[o_id])
        dp = sample_point(lookup[d_id])
        _, idx = tree.query(_latlon_to_unit_xyz([op.y, dp.y], [op.x, dp.x]))
        trip = Trip((op.x, op.y), (dp.x, dp.y), datetime(2000, 1, 1))
        trip.origin_cell, trip.destination_cell = ids[int(idx[0])], ids[int(idx[1])]
        trips.append(trip)
    return TravelDemand(trips)


def load_mtc_case(taz_path, trips_path, *, fraction=0.5, seed=42,
                  grid_size=200, largest_component=True, entry_taz_ids=(52, 17, 149, 168),
                  expected_tiles=None, progress=True):
    """Map endpoints to the full grid, sample trips, then discard outside endpoints."""
    from .demand import sample_demand
    taz = gpd.read_file(taz_path)
    city, sf_taz, full_centroids = _build_sf_grid(taz, grid_size, 1, largest_component)
    if expected_tiles is not None and len(city.cells) != expected_tiles:
        raise ValueError(f'SF grid has {len(city.cells)} tiles, expected {expected_tiles}. '
                         'Verify TAZ input and preprocessing choices.')
    trips = pd.read_csv(trips_path)
    required = {'orig_taz','dest_taz','trip_mode','depart_hour'}
    if not required <= set(trips.columns):
        raise ValueError(f'Trip file missing columns {sorted(required - set(trips.columns))}')
    trips = trips[trips['dest_taz'].isin(sf_taz['taz1454']) &
                  (trips['trip_mode'] < 7) & (trips['depart_hour'] < 12)].copy()
    trips = reroute_outside_origins_to_entry_taz(trips, sf_taz, taz, entry_taz_ids)
    demand = generate_synthetic_demand_from_trip_list_simple(
        city, trips, sf_taz, full_centroids, seed=seed, progress=progress)
    sampled = sample_demand(demand, fraction=fraction, seed=seed)
    retained = city.cell_dict
    demand = TravelDemand([
        trip for trip in sampled.trips
        if trip.origin_cell in retained and trip.destination_cell in retained
    ])
    if progress:
        print(
            f'Sampled {len(sampled.trips):,} trips | '
            f'Excluded {len(sampled.trips) - len(demand.trips):,} outside the city grid',
            flush=True,
        )
    city.assign_demand_by_cell(demand)
    city.set_protected_area(retained.keys())
    return city, demand, {tile: full_centroids[tile] for tile in retained}
