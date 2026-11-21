"""Matplotlib plots of the original tile-based model."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def plot_cordon(city, enclosed, *, ax=None, title=None):
    """Plot retained tiles; dark tiles indicate the enclosed region."""
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 7))
    for cell in city.cells:
        x, y = cell.polygon.bounds[:2]
        ax.add_patch(Rectangle((x, y), city.cell_size, city.cell_size,
                               facecolor='#275d8c' if cell.id in enclosed else '#e3edf4',
                               linewidth=0, zorder=1))
    # Highlight only internal graph-cut edges (waterfront boundaries cost zero).
    graph = city.build_graph(connectivity=4)
    for node in enclosed:
        i, j = node
        x, y, s = i*city.cell_size, j*city.cell_size, city.cell_size
        for neighbor, endpoints in [((i-1,j), ((x,y),(x,y+s))),
                                     ((i+1,j), ((x+s,y),(x+s,y+s))),
                                     ((i,j-1), ((x,y),(x+s,y))),
                                     ((i,j+1), ((x,y+s),(x+s,y+s)))]:
            if neighbor in graph and neighbor not in enclosed:
                (x1,y1),(x2,y2) = endpoints
                ax.plot([x1,x2],[y1,y2], color='#0b2438', linewidth=1.1)
    ax.autoscale_view()
    ax.set_aspect('equal')
    ax.axis('off')
    if title:
        ax.set_title(title)
    return ax


def save_comparison(city, start, end, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    plot_cordon(city, start, ax=axes[0], title='Initial cordon')
    plot_cordon(city, end, ax=axes[1], title='Optimized cordon')
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def save_history(result, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot([r['phase'] for r in result.phase_history],
            [r['captured_trips'] for r in result.phase_history], marker='.', lw=1.2)
    ax.set_xlabel('Annealing phase')
    ax.set_ylabel('Captured inbound trips')
    ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path
