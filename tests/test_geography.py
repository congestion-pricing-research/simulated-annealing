import geopandas as gpd
from shapely.geometry import box
from cordon_annealing.city import City
from cordon_annealing.geography import (map_cells_and_taz_by_bbox,
                                         filter_city_to_taz_area,
                                         filter_city_to_largest_component,
                                         load_mtc_case)


def test_taz_mask_filters_cells():
    city=City(4,4,1)
    sf=gpd.GeoDataFrame({'county':['san francisco'],'taz1454':[1]},
                        geometry=[box(-122.5,37.7,-122.48,37.72)],crs='EPSG:4326')
    mapping,_=map_cells_and_taz_by_bbox(city,sf)
    filter_city_to_taz_area(city,mapping,sf)
    assert 0 < len(city.cells) <= 16
    graph=city.build_graph(connectivity=4)
    assert len(graph)==len(city.cells)


def test_largest_connected_component():
    city=City(4,4,1)
    keep={(0,0),(0,1),(1,0),(3,3)}
    city.cells=[c for c in city.cells if c.id in keep]
    city.cell_dict={c.id:c for c in city.cells}
    remaining=filter_city_to_largest_component(city)
    assert remaining=={(0,0),(0,1),(1,0)}


def test_full_grid_mapping_samples_before_discarding_outside_endpoints(tmp_path):
    zones = gpd.GeoDataFrame(
        {'county': ['san francisco', 'san francisco'], 'taz1454': [10, 20]},
        geometry=[
            box(-122.50, 37.70, -122.48, 37.72),
            box(-122.469, 37.731, -122.46, 37.74),
        ],
        crs='EPSG:4326',
    )
    zone_path = tmp_path / 'zones.geojson'
    zones.to_file(zone_path)
    trips_path = tmp_path / 'trips.csv'
    trips_path.write_text(
        'orig_taz,dest_taz,trip_mode,depart_hour\n'
        '20,10,1,8\n'
        '10,10,1,8\n'
        '10,10,1,8\n'
        '10,10,1,8\n'
        '10,20,1,8\n'
        '10,10,1,8\n',
        encoding='utf-8',
    )
    city, demand, centroids = load_mtc_case(
        zone_path, trips_path, grid_size=4, fraction=0.5, seed=42,
        expected_tiles=4, progress=False,
    )
    assert set(city.cell_dict) == set(centroids) == {(0, 0), (0, 1), (1, 0), (1, 1)}
    # Seed 42 selects rows 6, 1 and 5. Rows 1 and 5 touch the excluded zone.
    assert len(demand.trips) == city.total_trips() == 1
    assert sum(len(tile.destination_trips) for tile in city.cells) == 1
