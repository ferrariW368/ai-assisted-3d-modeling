// Parametric support strap: two oval eyes joined by a curved body.
// Datum: centre of the left eye at (0,0), base at Z=0, thickness along +Z. Units: mm.
// All values below are example values. In a real job each value is tagged as
// MEASURED (taken from the physical part) or PLACEHOLDER (not measured yet,
// present only so the pipeline can run end to end).

total_length   = 150.0; // example, end to end
eye_outer_long = 30.0;  // example
eye_outer_short= 14.0;  // example
hole_long      = 20.0;  // example
hole_short     = 9.0;   // example
thickness      = 5.0;   // example
body_width     = 8.0;   // example
bow            = 10.0;  // example, Y offset of the body at mid-span
embed          = 3.0;   // how far the body runs into each eye wall
$fn            = 96;

centre_distance = total_length - eye_outer_long;

// Fail loudly on physically impossible input instead of rendering garbage.
assert(hole_long  < eye_outer_long,  "hole (long axis) must be smaller than the eye");
assert(hole_short < eye_outer_short, "hole (short axis) must be smaller than the eye");
assert(body_width < eye_outer_short, "body cannot be wider than the eye");
echo(centre_distance = centre_distance);

module eye(cx) {
    translate([cx, 0, 0])
    linear_extrude(height = thickness)
    difference() {
        scale([eye_outer_long / 2, eye_outer_short / 2]) circle(r = 1);
        scale([hole_long / 2, hole_short / 2]) circle(r = 1);
    }
}

// Parabolic centre line: y = 0 at both ends, y = bow at mid-span.
function yc(x, xs, xe) = bow * (1 - pow((x - (xs + xe) / 2) / ((xe - xs) / 2), 2));

module body() {
    xs = eye_outer_long / 2 - embed;
    xe = centre_distance - eye_outer_long / 2 + embed;
    n = 40;
    xl  = [for (i = [0 : n]) xs + (xe - xs) * i / n];
    top = [for (x = xl) [x, yc(x, xs, xe) + body_width / 2]];
    bot = [for (x = xl) [x, yc(x, xs, xe) - body_width / 2]];
    linear_extrude(height = thickness)
        polygon(concat(top, [for (i = [n : -1 : 0]) bot[i]]));
}

union() {
    eye(0);
    eye(centre_distance);
    body();
}
