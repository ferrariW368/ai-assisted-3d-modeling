"""Reject impossible measurements before they reach the CAD model (standard library only).

The same rules as the asserts in strap.scad, applied earlier so that a typo
coming from a form or chat message never produces a model at all.

Usage:
    python check_inputs.py total_length=150 eye_outer_long=30 ...
"""
import sys

REQUIRED = ("total_length", "eye_outer_long", "eye_outer_short",
            "hole_long", "hole_short", "thickness", "body_width")


def check_inputs(p):
    errs = [f"missing: {k}" for k in REQUIRED if k not in p]
    errs += [f"{k} must be a positive number (got {v!r})"
             for k, v in p.items() if not isinstance(v, (int, float)) or v <= 0]
    if errs:
        return errs
    if p["hole_long"] >= p["eye_outer_long"]:
        errs.append("hole_long must be smaller than eye_outer_long")
    if p["hole_short"] >= p["eye_outer_short"]:
        errs.append("hole_short must be smaller than eye_outer_short")
    if p["body_width"] >= p["eye_outer_short"]:
        errs.append("body_width cannot exceed eye_outer_short")
    if p["total_length"] <= 2 * p["eye_outer_long"]:
        errs.append("total_length is shorter than two eyes: the body does not fit")
    return errs


if __name__ == "__main__":
    params = {}
    for arg in sys.argv[1:]:
        k, _, v = arg.partition("=")
        try:
            params[k] = float(v.replace(",", "."))
        except ValueError:
            params[k] = v
    problems = check_inputs(params)
    print("\n".join(problems) if problems else "ok")
    sys.exit(1 if problems else 0)
