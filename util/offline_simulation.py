"""Finite, sequential multi-layer preview with no printer or Wi-Fi calls."""
import json
import queue
import threading

from shapely.geometry import mapping
from util.initial_assignments import validate_initial_assignments
from util.gcode_input import TOTAL_LAYERS, layer_of
from util.execution import RECOVERY_PLAN

from conflict_detect.collision_utils import sim_px
from kinematics.animation_simulation import animation_simulation
from util.command_script import (
    PHYSICAL_BOUNDS, collides_with_stored, mark_gcode_unavailable,
    pick_command_px, polygon_at_position, simulate_candidate,
)


def run_offline(printer, config, headless=False, initial_assignments=None):
    initial_pending = validate_initial_assignments(printer, initial_assignments)
    positions = {p: (300.0, 0.0) for p in printer}
    frames = None if headless else queue.Queue()
    accepted = []
    rejected = 0
    attempts = []
    counts = {p: 0 for p in printer}
    layer = 1
    completed_layers = []
    recovered_since_progress = False

    def has_work(q):
        return any(
            value[0] == "A" and layer_of(name) == layer
            for name, value in printer[q].codes.items()
        )

    def parking_positions():
        # Offline preview uses route endpoints; it does not replay recovery motion.
        return {q: tuple(route[-1]) for q, route in RECOVERY_PLAN}

    with (config.log_dir / "order.txt").open("w", encoding="utf-8") as log:
        for p, candidate in sorted(initial_pending.items()):
            log.write(f"initial assignment p{p}:{candidate}\n")
        while True:
            progressed = False
            for p in sorted(printer):
                sim_px(p, printer[p].codes, positions, config, layer)
                excluded = set()
                while True:
                    forced = bool(initial_pending)
                    if forced:
                        candidate = initial_pending.get(p)
                    else:
                        candidate = pick_command_px(p, printer, positions,
                                                    b=counts[p] == 0, excluded=excluded, layer=layer)
                    if candidate is None:
                        break
                    stored = {q: polygon_at_position(q, printer, pos)
                              for q, pos in positions.items()}
                    sweep, final = simulate_candidate(p, candidate, printer, positions,
                                                      config, simulation_queue=frames)
                    collisions = collides_with_stored(sweep, p, stored)
                    attempts.append({"printer": p, "gcode": candidate, "positions": dict(positions),
                                     "accepted": not bool(collisions), "collisions": collisions})
                    log.write(f"candidate p{p}:{candidate}; positions={positions}; "
                              f"accepted={not bool(collisions)}; collisions={collisions}\n")
                    if frames is not None:
                        frames.put({
                            "type": "result", "printer": p, "gcode": candidate,
                            "positions": final, "accepted": not bool(collisions),
                            "overlap": sum(collisions.values()), "collisions": collisions,
                            "physical_bounds": PHYSICAL_BOUNDS,
                            "candidate_polygon": mapping(sweep),
                            "stored_polygons": {q: mapping(poly) for q, poly in stored.items() if q != p},
                            "overlap_polygons": {q: mapping(sweep.intersection(stored[q])) for q in collisions},
                        })
                    if collisions:
                        rejected += 1
                        excluded.add(candidate)
                        log.write(f"reject p{p}:{candidate}; collision={collisions}\n")
                        if forced:
                            raise RuntimeError(f"Initial assignment p{p}:{candidate} failed collision checks: {collisions}")
                        continue
                    initial_pending.pop(p, None)
                    if forced and not initial_pending:
                        log.write("initial assignments complete; normal scheduling begins\n")
                    mark_gcode_unavailable(candidate, printer)
                    positions = final
                    counts[p] += 1
                    accepted.append({"printer": p, "gcode": candidate})
                    log.write(f"simulate p{p}:{candidate}\n")
                    progressed = True
                    break
            # This preview completes accepted jobs sequentially before advancing.
            if not any(has_work(q) for q in printer):
                completed_layers.append(layer)
                positions = parking_positions()
                log.write(f"layer {layer} complete; simulated parking: {positions}\n")
                if layer == TOTAL_LAYERS:
                    break
                layer += 1
                recovered_since_progress = False
                continue
            if progressed:
                recovered_since_progress = False
            elif not recovered_since_progress:
                positions = parking_positions()
                recovered_since_progress = True
                log.write(f"layer {layer} blocked; simulated recovery: {positions}\n")
            else:
                log.write(f"layer {layer} still blocked after simulated recovery\n")
                break
    remaining = sorted({name for px in printer.values() for name, value in px.codes.items()
                        if value[0] == "A"})
    report = {"mode": "offline", "accepted": accepted, "rejected_attempts": rejected,
              "remaining_reachable_regions": remaining, "final_positions": positions, "attempts": attempts}
    report["completed_layers"] = completed_layers
    report["stopped_layer"] = None if layer in completed_layers else layer
    report_path = config.log_dir / "simulation_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Local simulation: {len(accepted)} regions accepted; {len(remaining)} blocked.")
    print(f"Report: {report_path}")
    if frames is not None:
        frames.put({"type": "stop"})
        animation_simulation(frames, threading.Event(), threading.Event(), printer)
    return report
