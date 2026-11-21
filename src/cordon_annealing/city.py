"""City grid, tile adjacency, and trip assignment."""

from shapely.geometry import Polygon, Point
import networkx as nx
import random
from datetime import datetime


class Cell:
    """
    Represents a spatial cell in the city grid.
    Attributes:
        id: Unique identifier (tuple of row, col).
        centroid: (x, y) coordinates of the cell's center.
        polygon: Shapely Polygon defining the cell boundary.
        protected: Boolean flag for Protected Area.
        enclosed: Boolean flag for Enclosed Area.
        trips: List of trips whose origins fall in this cell.
        destination_trips: List of trips whose destinations fall in this cell.
    """

    def __init__(
        self, id, row, col, centroid, polygon, protected=False, enclosed=False
    ):
        self.id = id
        self.row = row
        self.col = col
        self.centroid = centroid
        self.polygon = polygon
        self.protected = protected
        self.enclosed = enclosed
        self.trips = []
        self.destination_trips = []


class Trip:
    """
    Represents an individual trip demand.
    Attributes:
        origin: (x, y) tuple start coordinate.
        destination: (x, y) tuple end coordinate.
        start_time: datetime of trip start.
        origin_cell: ID of the cell where the trip starts.
        destination_cell: ID of the cell where the trip ends.
    """

    def __init__(self, origin, destination, start_time):
        self.origin = origin
        self.destination = destination
        self.start_time = start_time
        self.origin_cell = None
        self.destination_cell = None


class TravelDemand:
    """
    Holds a list of Trip objects.
    """

    def __init__(self, trips=None):
        self.trips = trips if trips else []

    def __add__(self, other):
        """
        Return a new TravelDemand combining trips from self and other.
        """
        if not isinstance(other, TravelDemand):
            return NotImplemented
        return TravelDemand(self.trips + other.trips)

    @classmethod
    def generate_uniform(cls, city, trips_per_cell):
        """
        Generates trips uniformly: each cell has trips_per_cell origins and destinations.
        """
        origins, destinations = [], []
        for cell in city.cells:
            for _ in range(trips_per_cell):
                minx, miny, maxx, maxy = cell.polygon.bounds
                while True:
                    x = random.uniform(minx, maxx)
                    y = random.uniform(miny, maxy)
                    if cell.polygon.contains(Point(x, y)):
                        origins.append((x, y))
                        break
            for _ in range(trips_per_cell):
                minx, miny, maxx, maxy = cell.polygon.bounds
                while True:
                    x = random.uniform(minx, maxx)
                    y = random.uniform(miny, maxy)
                    if cell.polygon.contains(Point(x, y)):
                        destinations.append((x, y))
                        break
        random.shuffle(destinations)
        now = datetime.now()
        trips = [Trip(o, d, now) for o, d in zip(origins, destinations)]
        return cls(trips)


def generate_iid_uniform(city, n_trips):
    # Draw *independently* an origin and a destination for each trip
    trips = []
    now = datetime.now()
    for _ in range(n_trips):
        ox, oy = random.uniform(0, city.width), random.uniform(0, city.height)
        dx, dy = random.uniform(0, city.width), random.uniform(0, city.height)
        trips.append(Trip((ox, oy), (dx, dy), now))
    return TravelDemand(trips)


class City:
    """
    Defines a city area partitioned into grid cells.
    """

    def __init__(self, width, height, cell_size, cell_shape_func=None):
        if width <= 0 or height <= 0 or cell_size <= 0:
            raise ValueError("City dimensions and cell size must be positive")
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.cells = []
        self.cell_dict = {}
        self._create_cells(cell_shape_func)

    def _create_cells(self, cell_shape_func=None):
        cols = int(self.width / self.cell_size)
        rows = int(self.height / self.cell_size)
        for i in range(cols):
            for j in range(rows):
                x0, y0 = i * self.cell_size, j * self.cell_size
                x1, y1 = x0 + self.cell_size, y0 + self.cell_size
                centroid = (x0 + self.cell_size / 2, y0 + self.cell_size / 2)
                poly = (
                    cell_shape_func(x0, y0, x1, y1)
                    if cell_shape_func
                    else Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
                )
                cell = Cell(id=(i, j), row=i, col=j, centroid=centroid, polygon=poly)
                self.cells.append(cell)
                self.cell_dict[(i, j)] = cell

    def assign_demand(self, demand: TravelDemand):
        """
        Assigns each Trip to origin and destination cells.
        """
        for cell in self.cells:
            cell.trips.clear()
            cell.destination_trips.clear()
        for trip in demand.trips:
            # origin
            op = Point(trip.origin)
            for cell in self.cells:
                if cell.polygon.contains(op):
                    trip.origin_cell = cell.id
                    cell.trips.append(trip)
                    break
            # destination
            dp = Point(trip.destination)
            for cell in self.cells:
                if cell.polygon.contains(dp):
                    trip.destination_cell = cell.id
                    cell.destination_trips.append(trip)
                    break

    def assign_demand_by_cell(
        self, demand: TravelDemand, ignore_missing_centroids=False
    ):
        """
        Assigns each Trip to its origin and destination cells
        using trip.origin_cell and trip.destination_cell, without
        any spatial contains() checks.

        Parameters:
        - demand: TravelDemand object containing trips
        - ignore_missing_centroids (bool): If True, skips trips whose centroids are not in cell_dict
        """

        for cell in self.cells:
            cell.trips.clear()
            cell.destination_trips.clear()
        for trip in demand.trips:
            # origin
            o_cid = trip.origin_cell
            if o_cid not in self.cell_dict:
                if ignore_missing_centroids:
                    continue
                else:
                    raise KeyError(f"Origin cell {o_cid} not found in cell_dict")

            # Validate both endpoints before assigning either one.
            d_cid = trip.destination_cell
            if d_cid not in self.cell_dict:
                if ignore_missing_centroids:
                    continue
                else:
                    raise KeyError(f"Destination cell {d_cid} not found in cell_dict")

            self.cell_dict[o_cid].trips.append(trip)
            self.cell_dict[d_cid].destination_trips.append(trip)

    def total_trips(self):
        """Total number of trips (by origin)."""
        return sum(len(cell.trips) for cell in self.cells)

    def compute_commuters(self):
        """Trips ending in the Protected Area."""
        return sum(len(cell.destination_trips) for cell in self.cells if cell.protected)

    def compute_captured_commuters(self):
        """
        Captured commuters: origin outside EA and destination in both EA and PA.
        """
        count = 0
        for cell in self.cells:
            if cell.enclosed and cell.protected:
                for trip in cell.destination_trips:
                    orig = self.cell_dict.get(trip.origin_cell)
                    if orig and not orig.enclosed:
                        count += 1
        return count

    def build_graph(self, connectivity=8):
        """
        Builds a networkx Graph where each cell is a node.
        connectivity=8 includes diagonals; connectivity=4 only cardinal directions.
        Node attributes include protected and enclosed flags.
        """
        G = nx.Graph()
        # add nodes
        for nid, cell in self.cell_dict.items():
            G.add_node(nid, protected=cell.protected, enclosed=cell.enclosed)
        # define neighbor offsets
        if connectivity == 8:
            offsets = [
                (di, dj)
                for di in [-1, 0, 1]
                for dj in [-1, 0, 1]
                if not (di == 0 and dj == 0)
            ]
        elif connectivity == 4:
            offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        else:
            raise ValueError("connectivity must be 4 or 8")
        # add edges
        for i, j in self.cell_dict:
            for di, dj in offsets:
                nbr = (i + di, j + dj)
                if nbr in self.cell_dict:
                    G.add_edge((i, j), nbr)
        return G

    def set_protected_area(self, protected_nodes):
        protected_set = set(protected_nodes)
        if not protected_set <= self.cell_dict.keys():
            raise ValueError("Protected area includes unknown cells")
        for cell_id, cell in self.cell_dict.items():
            cell.protected = cell_id in protected_set

    def set_enclosed_area(self, enclosed_nodes):
        enclosed_set = set(enclosed_nodes)
        if not enclosed_set <= self.cell_dict.keys():
            raise ValueError("Enclosed area includes unknown cells")
        for cell_id, cell in self.cell_dict.items():
            cell.enclosed = cell_id in enclosed_set


