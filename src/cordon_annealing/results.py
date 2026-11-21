"""Structured output and provenance for optimization runs."""
import csv
from dataclasses import asdict
import json
from pathlib import Path

from .initialization import write_ea_csv
from .plotting import save_comparison, save_history


def _write_csv(path, rows):
    if not rows:
        return
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save_result(city, result, config, output_dir, *, label='optimization'):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    write_ea_csv(output / 'initial_cordon.csv', result.initial_ea)
    write_ea_csv(output / 'optimized_cordon.csv', result.final_ea)
    _write_csv(output / 'phase_history.csv', result.phase_history)
    step_history_path = output / 'step_history.csv'
    if result.step_history:
        _write_csv(step_history_path, result.step_history)
    else:
        step_history_path.unlink(missing_ok=True)
    payload = {
        'label': label, 'active_grid_tiles': len(city.cells),
        'initial': result.initial_metrics, 'final': result.final_metrics,
        'config': asdict(config),
        'definitions': {'boundary_edges': 'Only 4-neighbor graph edges crossing the enclosed area; coastline/exterior graph edges not counted.'},
    }
    (output / 'summary.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    save_comparison(city, result.initial_ea, result.final_ea, output/'cordons.png')
    save_history(result, output/'phase_history.png')
    return payload
