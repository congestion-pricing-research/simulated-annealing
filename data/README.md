# Input formats

The bundled `example_od.csv` is a synthetic origin–destination (OD) table for a 4 × 4 grid. It uses the columns `origin_i,origin_j,dest_i,dest_j,count` and zero-based tile indices.

A starting mask uses the columns `i,j` with one enclosed tile per row. The installed package includes `data/sf_start.csv` as the default San Francisco mask.

See the [San Francisco setup](../README.md#san-francisco-data) for the external zone geometry and individual trip files.
