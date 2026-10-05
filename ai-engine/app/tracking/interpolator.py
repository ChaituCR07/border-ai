from typing import List, Tuple


def interpolate_trail(points: List[Tuple[float, float, float]], max_time_gap_s: float = 0.5,
                      step_time_s: float = 0.05) -> List[Tuple[float, float, float]]:
    """Linearly interpolate missing points along a trajectory trail.

    Args:
        points: List of (timestamp, x, y) tuples sorted by timestamp.
        max_time_gap_s: Maximum temporal gap to bridge. Larger gaps are left untouched.
        step_time_s: Temporal resolution for interpolated points.

    Returns:
        New list of (timestamp, x, y) points including interpolated steps.
    """
    if len(points) < 2:
        return list(points)

    result = [points[0]]
    for i in range(1, len(points)):
        t_prev, x_prev, y_prev = result[-1]
        t_curr, x_curr, y_curr = points[i]
        dt = t_curr - t_prev

        if step_time_s < dt <= max_time_gap_s:
            steps = int(dt // step_time_s)
            for s in range(1, steps):
                alpha = (s * step_time_s) / dt
                t_interp = t_prev + s * step_time_s
                x_interp = x_prev + alpha * (x_curr - x_prev)
                y_interp = y_prev + alpha * (y_curr - y_prev)
                result.append((round(t_interp, 4), round(x_interp, 2), round(y_interp, 2)))

        result.append(points[i])

    return result
