"""UrbGEN iterative placement of rotated RECTANGLES in a single planar site.

Outputs only geometric parameters for NATIVE Visual Scripting geometry nodes.
All distances are in Allplan model-coordinate units (typically mm).
The 2-D solver checks polygon containment, overlap and optional outline clearance.
Geometric approximations of Vorarlberg BFZ/BNZ, not a legal compliance check.
"""
import math
from functools import lru_cache
import random
import NemAll_Python_Geometry as Geo
from NodeUtil import NodeBase

NodeBase.trace_node_name('NodeUrbGENIterativePlacement')


def create_node(init_data):
    return NodeUrbGENIterativePlacement(init_data)


EPS = 1e-8
# Allplan model units are millimetres: 10 mm = 1 cm.
CM_GRID = 10.0


def cm_round(value):
    """Round a model-coordinate length to the nearest full centimetre."""
    value = float(value)
    return float(math.floor(value / CM_GRID + 0.5) * CM_GRID)


def cm_grid_bounds(low, high):
    """Choose centimetre sizes strictly within the user supplied limits."""
    min_step = math.ceil(float(low) / CM_GRID - 1e-10)
    max_step = math.floor(float(high) / CM_GRID + 1e-10)
    if min_step > max_step:
        raise ValueError('No centimetre increment fits into Min/Max Length or Width bounds')
    return int(min_step), int(max_step)



def vertices_from_boundary(boundary):
    if not isinstance(boundary, Geo.Polygon3D):
        raise TypeError('Boundary needs a single Polygon3D (buildable boundary)')
    pts = [(float(boundary.GetPoint(i).X), float(boundary.GetPoint(i).Y),
            float(boundary.GetPoint(i).Z)) for i in range(int(boundary.Count()))]
    if len(pts) > 1 and math.dist(pts[0][:2],pts[-1][:2]) <= EPS:
        pts.pop()
    if len(pts) < 3:
        raise ValueError('Boundary requires at least three distinct vertices')
    if not all(math.isfinite(v) for pt in pts for v in pt):
        raise ValueError('Non-finite boundary coordinates')
    if max(p[2] for p in pts)-min(p[2] for p in pts)>0.001:
        raise ValueError('Boundary must be horizontal; use a planar polygon')
    coords = [(p[0],p[1]) for p in pts]
    if abs(signed_area(coords))<EPS:
        raise ValueError('Boundary has zero area')
    if any(length2(coords[i],coords[(i+1)%len(coords)])<=EPS for i in range(len(coords))):
        raise ValueError('Boundary contains a zero-length edge')
    for i in range(len(coords)):
        for j in range(i+1,len(coords)):
            if j==i+1 or (i==0 and j==len(coords)-1):
                continue
            if segments_intersect(coords[i],coords[(i+1)%len(coords)],
                                  coords[j],coords[(j+1)%len(coords)]):
                raise ValueError('Self-intersecting boundary polygon')
    return coords, pts[0][2]


def signed_area(points):
    return 0.5*sum(points[i][0]*points[(i+1)%len(points)][1]-
                   points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))


def length2(a,b):
    return (a[0]-b[0])**2+(a[1]-b[1])**2


def cross(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def point_on_segment(p,a,b):
    return abs(cross(a,b,p))<=EPS*max(1,math.sqrt(length2(a,b))) and \
           min(a[0],b[0])-EPS<=p[0]<=max(a[0],b[0])+EPS and \
           min(a[1],b[1])-EPS<=p[1]<=max(a[1],b[1])+EPS


def segments_intersect(a,b,c,d):
    c1,c2,c3,c4=cross(a,b,c),cross(a,b,d),cross(c,d,a),cross(c,d,b)
    if (c1>EPS and c2<-EPS or c1<-EPS and c2>EPS) and \
       (c3>EPS and c4<-EPS or c3<-EPS and c4>EPS):
        return True
    return any((point_on_segment(p,u,v) for p,u,v in ((c,a,b),(d,a,b),(a,c,d),(b,c,d))))


def point_inside(p, poly):
    # Boundary points count as contained, so a zero-clearance touching building is allowed.
    inside=False
    x,y=p
    for i,a in enumerate(poly):
        b=poly[(i+1)%len(poly)]
        if point_on_segment(p,a,b):
            return True
        if (a[1]>y)!=(b[1]>y):
            hit_x=a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if hit_x>x:
                inside=not inside
    return inside


def segment_distance(a,b,c,d):
    if segments_intersect(a,b,c,d):
        return 0.0
    def p_to_seg(p,u,v):
        dx,dy=v[0]-u[0],v[1]-u[1]
        t=max(0,min(1,((p[0]-u[0])*dx+(p[1]-u[1])*dy)/(dx*dx+dy*dy)))
        return math.hypot(p[0]-(u[0]+t*dx),p[1]-(u[1]+t*dy))
    return min(p_to_seg(a,c,d),p_to_seg(b,c,d),p_to_seg(c,a,b),p_to_seg(d,a,b))


def edges(poly):
    return [(poly[i],poly[(i+1)%len(poly)]) for i in range(len(poly))]


def polygon_distance(poly_a,poly_b):
    # Check nesting first, otherwise two nested footprints report positive edge distance.
    if point_inside(poly_a[0],poly_b) or point_inside(poly_b[0],poly_a):
        return 0.0
    return min(segment_distance(a,b,c,d) for a,b in edges(poly_a) for c,d in edges(poly_b))


def entirely_inside(building,boundary):
    # Vertex-only tests are insufficient for concave boundaries.
    if not all(point_inside(p,boundary) for p in building):
        return False
    for a,b in edges(building):
        if not point_inside(((a[0]+b[0])/2,(a[1]+b[1])/2),boundary):
            return False
        for c,d in edges(boundary):
            # Any genuine, non-collinear crossing makes the footprint invalid.
            ca,cb=cross(a,b,c),cross(a,b,d)
            cc,cd=cross(c,d,a),cross(c,d,b)
            if ((ca>EPS and cb<-EPS) or (ca<-EPS and cb>EPS)) and \
               ((cc>EPS and cd<-EPS) or (cc<-EPS and cd>EPS)):
                return False
    return True


def rectangle(x,y,length,width,angle_deg):
    # Placement point is the local rectangle corner. Native Rotate must use this point.
    theta=math.radians(angle_deg)
    cs,sn=math.cos(theta),math.sin(theta)
    corners=((0,0),(length,0),(length,width),(0,width))
    return [(x+u*cs-v*sn,y+u*sn+v*cs) for u,v in corners]



def typology_outline(code, length, width, arm_ratio=1.3):
    """Return (outer points, optional courtyard hole); local XY coordinates.

    Typology codes follow UrbGEN (0 I,1 L,2 T,3 H,4 C,5 Plus,7 courtyard).
    This is an approximated parametric geometry, not the original closed-source solver.
    """
    le, wi = float(length), float(width)
    if le <= 0 or wi <= 0: raise ValueError('Length and Width must be > 0')
    if not 0.3 <= arm_ratio <= 8: raise ValueError('ArmLengthRatio must be 0.3..8')
    # Bar thickness varies with arm length ratio and is kept positive.
    d = min(le, wi) / (1.3 + arm_ratio)
    d = max(10.0, min(d, 0.44 * min(le, wi)))
    x1, x2 = d, le-d
    y1, y2 = d, wi-d
    cx1, cx2 = le/2-d/2, le/2+d/2
    cy1, cy2 = wi/2-d/2, wi/2+d/2
    if code == 0:
        return [(0,0),(le,0),(le,wi),(0,wi)], []
    if code == 1:
        return [(0,0),(le,0),(le,d),(d,d),(d,wi),(0,wi)], []
    if code == 2:
        return [(cx1,0),(cx2,0),(cx2,y2),(le,y2),(le,wi),(0,wi),(0,y2),(cx1,y2)], []
    if code == 3:
        return [(0,0),(x1,0),(x1,cy1),(x2,cy1),(x2,0),(le,0),
                (le,wi),(x2,wi),(x2,cy2),(x1,cy2),(x1,wi),(0,wi)], []
    if code == 4:
        return [(0,0),(le,0),(le,wi),(x2,wi),(x2,y1),(x1,y1),(x1,wi),(0,wi)], []
    if code == 5:
        return [(cx1,0),(cx2,0),(cx2,cy1),(le,cy1),(le,cy2),(cx2,cy2),
                (cx2,wi),(cx1,wi),(cx1,cy2),(0,cy2),(0,cy1),(cx1,cy1)], []
    if code == 7:
        return [(0,0),(le,0),(le,wi),(0,wi)], [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]
    raise ValueError('Typology code must be 0..5 or 7 (6 means mixed selection)')


def rotate_translate(poly, x, y, angle):
    rad=math.radians(float(angle)); co,si=math.cos(rad),math.sin(rad)
    return [(x+a*co-b*si, y+a*si+b*co) for a,b in poly]


def footprint_parts(code,x,y,le,wi,angle,arm_ratio):
    outer,hole=typology_outline(code,le,wi,arm_ratio)
    return rotate_translate(outer,x,y,angle), rotate_translate(hole,x,y,angle) if hole else []

def nearest_edge_angle(p,boundary):
    px,py=p
    best=None
    for a,b in edges(boundary):
        vx,vy=b[0]-a[0],b[1]-a[1]
        den=vx*vx+vy*vy
        if den<=EPS:continue
        t=max(0.0,min(1.0,((px-a[0])*vx+(py-a[1])*vy)/den))
        d2=(px-a[0]-t*vx)**2+(py-a[1]-t*vy)**2
        if best is None or d2<best[0]:
            best=(d2,math.degrees(math.atan2(vy,vx))%180.0)
    if best is None: raise ValueError('Cannot determine nearest edge')
    return best[1]


def _adjust_floors(accepted, site_area, target_far, min_floors, max_floors, ggf_factor=1.0):
    """Assign integer floors to approximate target eligible GGF; no geometric expansion."""
    if not accepted or target_far <= 0:
        return accepted
    footprints = [abs(signed_area(v[0])) for v in accepted]
    target_area = target_far * site_area / ggf_factor
    levels = [min_floors] * len(accepted)
    current = sum(a * min_floors for a in footprints)
    # Repeated single-floor changes with biggest error reduction first.
    while True:
        current_error = abs(target_area - current)
        choice = None
        for i, area in enumerate(footprints):
            if levels[i] >= max_floors:
                continue
            next_error = abs(target_area - (current + area))
            improvement = current_error - next_error
            if improvement > 1e-7 and (choice is None or improvement > choice[0]):
                choice = (improvement, i, area)
        if choice is None:
            break
        _, i, area = choice
        levels[i] += 1
        current += area
    return [(poly, x, y, le, wi, ang, levels[i], typ)
            for i, (poly, x, y, le, wi, ang, _, typ) in enumerate(accepted)]


def _generate_one(boundary, rng, target_count, len_steps, wid_steps,
                  min_distance, max_attempts, rotation_mode, fixed_angle,
                  min_floors, max_floors, target_bcr, site_area, enabled_typologies=(0,), arm_ratio=1.3):
    lo_x = min(p[0] for p in boundary)
    hi_x = max(p[0] for p in boundary)
    lo_y = min(p[1] for p in boundary)
    hi_y = max(p[1] for p in boundary)
    accepted = []
    accepted_bounds = []
    attempts = 0
    covered_area = 0.0
    nominal_area = target_bcr * site_area / target_count if target_bcr > 0 else None
    while attempts < max_attempts and len(accepted) < target_count:
        attempts += 1
        x = cm_round(rng.uniform(lo_x, hi_x))
        y = cm_round(rng.uniform(lo_y, hi_y))
        le = rng.randint(*len_steps) * CM_GRID
        # Select typology BEFORE dimensioning. For L/T/H/C/Plus shapes, bounding
        # rectangle area can be much larger than the actual footprint area.
        typology = rng.choice(enabled_typologies)
        if nominal_area is None:
            wi = rng.randint(*wid_steps) * CM_GRID
        else:
            # Find the cm-grid width whose TRUE typology polygon area best
            # matches the per-building target.  Small binary search avoids
            # exhaustive scanning of every allowable width (fast-preview safe).
            # Target is a symmetric goal, NOT a lower or upper bound.
            # Adapt to the area actually accepted so far. Sample both below
            # and above the remaining per-building goal; compare candidates
            # with ABSOLUTE BFZ error after placement.
            remaining = target_bcr * site_area - covered_area
            remaining_slots = max(1, target_count - len(accepted))
            wanted = max(0.0, remaining / remaining_slots) * rng.uniform(0.80, 1.25)
            low, high = wid_steps
            def area_at(step):
                outline, hole = typology_outline(typology, le, step * CM_GRID, arm_ratio)
                return abs(signed_area(outline)) - (abs(signed_area(hole)) if hole else 0.0)
            while low < high:
                mid = (low + high) // 2
                if area_at(mid) < wanted:
                    low = mid + 1
                else:
                    high = mid
            candidates = [k for k in (low - 1, low, low + 1) if wid_steps[0] <= k <= wid_steps[1]]
            best_step = min(candidates, key=lambda k: abs(area_at(k) - wanted))
            wi = best_step * CM_GRID
        floors = rng.randint(min_floors, max_floors)
        if rotation_mode == 0:
            angle = fixed_angle % 180.0
        elif rotation_mode == 1:
            angle = rng.uniform(0, 180)
        else:
            angle = (nearest_edge_angle((x, y), boundary) + fixed_angle) % 180
        # Choose exclusively among the checked typologies (0..5).
        # Code 7 (courtyard with hole) is not yet handled by the solver.
        outer, inner = footprint_parts(typology,x,y,le,wi,angle,arm_ratio)
        poly = outer
        if not entirely_inside(poly, boundary):
            continue
        # Fast conservative broad-phase: only detailed polygon checks for
        # buildings whose bounding boxes are within the minimum clearance.
        bx0 = min(pt[0] for pt in poly); bx1 = max(pt[0] for pt in poly)
        by0 = min(pt[1] for pt in poly); by1 = max(pt[1] for pt in poly)
        clearance = min_distance + 1e-7
        blocked = False
        for existing, (ex0, ex1, ey0, ey1) in zip(accepted, accepted_bounds):
            if bx1 + clearance < ex0 or ex1 + clearance < bx0 or \
               by1 + clearance < ey0 or ey1 + clearance < by0:
                continue
            if polygon_distance(poly, existing[0]) < clearance:
                blocked = True
                break
        if blocked:
            continue
        accepted.append((poly, x, y, le, wi, angle, floors, typology))
        covered_area += abs(signed_area(poly))
        accepted_bounds.append((bx0, bx1, by0, by1))
    return accepted, attempts


@lru_cache(maxsize=256)
def _generate_one_cached(boundary_key, trial_seed, target_count, len_steps, wid_steps,
                         min_distance, max_attempts, rotation_mode, fixed_angle,
                         min_floors, max_floors, target_bcr, site_area,
                         enabled_typologies, arm_ratio):
    """Cache expensive deterministic placements between palette changes.

    Cache key includes the actual boundary and all placement parameters.
    Floor-height, displayed variant, BNZ target and GGFFactor are intentionally
    excluded because they don't affect 2D placement; their computations run
    separately on the copied result. Bounded to avoid unbounded memory use.
    """
    return _generate_one(boundary_key, random.Random(trial_seed), target_count,
                         len_steps, wid_steps, min_distance, max_attempts,
                         rotation_mode, fixed_angle, min_floors, max_floors,
                         target_bcr, site_area, enabled_typologies, arm_ratio)


def generate_variants(boundary, target_count, min_length, max_length, min_width,
                      max_width, min_distance, max_attempts, variant_count,
                      base_seed, selected_variant, rotation_mode, fixed_angle,
                      min_floors, max_floors, floor_height, position_z=None,
                      target_bcr=0.0, target_far=0.0, optimization_trials=3, reference_area_m2=0.0, ggf_factor=1.0, enabled_typologies=(0,), arm_ratio=1.3, evaluation_mode=0):
    """Generate independently seeded alternatives and select best density trial.

    TargetBFZ/TargetBNZ use Austrian percentage indices (30, 120), 0 disables.
    BNZ is APPROXIMATE: eligible GGF = polygon footprint * floors * GGFFactor.
    BFZ approximates above-ground covered area by polygon footprints.
    """
    if not isinstance(boundary, (list, tuple)) or len(boundary) < 3:
        raise ValueError('Boundary vertices required')
    target_count = int(target_count)
    max_attempts = int(max_attempts)
    variant_count = int(variant_count)
    selected_variant = int(selected_variant)
    rotation_mode = int(rotation_mode)
    base_seed = int(base_seed)
    min_floors = int(min_floors)
    max_floors = int(max_floors)
    optimization_trials = int(optimization_trials)
    evaluation_mode = int(evaluation_mode)
    target_bcr = float(target_bcr) / 100.0
    reference_area_m2 = float(reference_area_m2)
    target_far = float(target_far) / 100.0
    ggf_factor = float(ggf_factor)
    enabled_typologies = tuple(sorted(set(int(t) for t in enabled_typologies)))
    arm_ratio = float(arm_ratio)
    for name, value in [('MinLength', min_length), ('MaxLength', max_length),
                        ('MinWidth', min_width), ('MaxWidth', max_width),
                        ('MinDistance', min_distance), ('FloorHeight', floor_height),
                        ('FixedAngle', fixed_angle), ('TargetBFZ', target_bcr),
                        ('TargetBNZ', target_far), ('NetGroundAreaM2', reference_area_m2), ('GGFFactor', ggf_factor)]:
        if not math.isfinite(float(value)):
            raise ValueError(name + ' must be finite')
    if not 1 <= target_count <= 500: raise ValueError('TargetCount must be 1..500')
    if not 1 <= max_attempts <= 100000: raise ValueError('MaxAttempts must be 1..100000')
    if not 1 <= variant_count <= 30: raise ValueError('VariantCount must be 1..30')
    if not 0 <= selected_variant < variant_count: raise ValueError('SelectedVariant outside range')
    if not enabled_typologies: raise ValueError('Mindestens eine Gebaeudeform muss aktiviert sein (EnableI/EnableL/EnableT/EnableH/EnableC/EnablePlus)')
    if any(t not in (0,1,2,3,4,5) for t in enabled_typologies): raise ValueError('Enabled typologies must be 0..5')
    if not 0.3 <= arm_ratio <= 8: raise ValueError('ArmLengthRatio must be 0.3..8')
    if not 0 <= rotation_mode <= 2: raise ValueError('RotationMode must be 0, 1 or 2')
    if not 1 <= optimization_trials <= 12: raise ValueError('OptimizationTrials must be 1..12')
    if evaluation_mode not in (0,1): raise ValueError('EvaluationMode must be 0 (fast preview) or 1 (full optimization)')
    if not 0 <= target_bcr <= 1: raise ValueError('TargetBFZ must be between 0 and 100')
    if target_far < 0: raise ValueError('TargetBNZ cannot be negative')
    if reference_area_m2 < 0: raise ValueError('NetGroundAreaM2 cannot be negative')
    if not 0 < ggf_factor <= 1: raise ValueError('GGFFactor must be in (0, 1]')
    if (target_bcr > 0 or target_far > 0) and reference_area_m2 <= 0:
        raise ValueError('NetGroundAreaM2 (legal NGF) is required for BFZ/BNZ targets')
    if min_length <= 0 or min_width <= 0 or max_length < min_length or max_width < min_width:
        raise ValueError('Invalid length/width bounds')
    if min_distance < 0: raise ValueError('MinDistance cannot be negative')
    if not 1 <= min_floors <= max_floors <= 200: raise ValueError('Invalid floor count range')
    if floor_height <= 0: raise ValueError('FloorHeight must be positive')
    len_steps = cm_grid_bounds(min_length, max_length)
    wid_steps = cm_grid_bounds(min_width, max_width)
    rounded_floor_height = cm_round(floor_height)
    if rounded_floor_height <= 0:
        raise ValueError('FloorHeight below 1 cm after rounding')
    buildable_area = abs(signed_area(boundary))
    if buildable_area <= EPS: raise ValueError('Zero buildable area')
    # Reference area is the full parcel area, supplied in square metres.
    site_area = reference_area_m2 * 1_000_000.0 if reference_area_m2 > 0 else buildable_area
    selected = None
    counts, completes, attempt_counts, seeds = [], [], [], []
    bcr_values, far_values, bcr_errors, far_errors, scores = [], [], [], [], []
    any_target = target_bcr > 0 or target_far > 0
    # Fast preview computes ONE placement for the selected variant only.
    # Other metrics use -1 sentinel, i.e. NOT COMPUTED, never 0 (which is a valid value).
    # Full optimization keeps prior semantics and evaluates all variants/trials.
    for variant in range(variant_count):
        seed = base_seed + variant
        if evaluation_mode == 0 and variant != selected_variant:
            counts.append(-1); completes.append(False); attempt_counts.append(-1)
            seeds.append(seed); bcr_values.append(-1.0); far_values.append(-1.0)
            bcr_errors.append(-1.0); far_errors.append(-1.0); scores.append(-1.0)
            continue
        # If density targets disabled: exact old behavior, one placement run.
        trials = (optimization_trials if any_target else 1) if evaluation_mode == 1 else 1
        best = None
        for trial in range(trials):
            trial_seed = seed if trial == 0 else (seed + trial * 1000003)
            buildings, attempts = _generate_one_cached(
                tuple((float(x), float(y)) for x, y in boundary), trial_seed,
                target_count, len_steps, wid_steps, min_distance, max_attempts,
                rotation_mode, fixed_angle, min_floors, max_floors,
                target_bcr, site_area, enabled_typologies, arm_ratio)
            buildings = _adjust_floors(buildings, site_area, target_far,
                                      min_floors, max_floors, ggf_factor)
            covered = sum(abs(signed_area(v[0])) for v in buildings)
            gross_floor = sum(abs(signed_area(v[0])) * v[6] for v in buildings)
            bcr = covered / site_area
            far = gross_floor * ggf_factor / site_area
            bcr_error = abs(bcr - target_bcr) if target_bcr > 0 else 0.0
            far_error = abs(far - target_far) if target_far > 0 else 0.0
            # Equal relative emphasis for enabled targets, modest penalty for
            # fewer placed buildings. No false claims of target feasibility.
            score = ((bcr_error / target_bcr if target_bcr else 0.0) +
                     (far_error / target_far if target_far else 0.0) +
                     0.25 * (target_count - len(buildings)) / target_count)
            if not any_target:
                score = (target_count - len(buildings)) / target_count
            candidate = (score, buildings, attempts, bcr, far, bcr_error, far_error)
            if best is None or score < best[0] - 1e-12:
                best = candidate
        score, buildings, attempts, bcr, far, bcr_error, far_error = best
        counts.append(len(buildings))
        completes.append(len(buildings) == target_count)
        attempt_counts.append(attempts)
        seeds.append(seed)
        bcr_values.append(100.0 * bcr)
        far_values.append(100.0 * far)
        bcr_errors.append(100.0 * bcr_error)
        far_errors.append(100.0 * far_error)
        scores.append(score)
        if variant == selected_variant: selected = buildings
    selected = selected or []
    xs = [v[1] for v in selected]
    ys = [v[2] for v in selected]
    lengths = [v[3] for v in selected]
    widths = [v[4] for v in selected]
    rotations = [v[5] for v in selected]
    floors = [v[6] for v in selected]
    heights = [v[6] * rounded_floor_height for v in selected]
    typologies = [v[7] for v in selected]
    return (xs, ys, [cm_round(position_z if position_z is not None else 0.0)] * len(selected),
            lengths, widths, rotations, floors, heights, counts, completes,
            attempt_counts, seeds, len(selected), completes[selected_variant],
            bcr_values, far_values, bcr_errors, far_errors, scores,
            buildable_area / 1000000.0, site_area / 1000000.0, typologies)


class NodeUrbGENIterativePlacement(NodeBase):
    def _create_output(self):
        p=self.build_ele
        names=('X','Y','Z','Lengths','Widths','AnglesDeg','Floors','Heights',
               'VariantCounts','VariantComplete','VariantAttempts','VariantSeeds',
               'SelectedCount','SelectedComplete','VariantBFZ','VariantBNZ',
               'VariantBFZError','VariantBNZError','VariantScores','SiteAreaM2',
               'NetGroundAreaUsedM2','TypologyCodes',
               'IsValid','ErrorMessage')
        for name in names:self._set_init_node_output(getattr(p,name))
        try:
            boundary,z=vertices_from_boundary(p.Boundary.value)
            result=generate_variants(
                boundary,p.TargetCount.value,p.MinLength.value,p.MaxLength.value,
                p.MinWidth.value,p.MaxWidth.value,p.MinDistance.value,
                p.MaxAttempts.value,p.VariantCount.value,p.BaseSeed.value,
                p.SelectedVariant.value,p.RotationMode.value,p.FixedAngle.value,
                p.MinFloors.value,p.MaxFloors.value,p.FloorHeight.value,z,
                p.TargetBFZ.value,p.TargetBNZ.value,p.OptimizationTrials.value,
                p.NetGroundAreaM2.value,p.GGFFactor.value,
                tuple(i for i, enabled in enumerate((p.EnableI.value,p.EnableL.value,
                  p.EnableT.value,p.EnableH.value,p.EnableC.value,p.EnablePlus.value)) if enabled),
                p.ArmLengthRatio.value,p.EvaluationMode.value)
            for name,value in zip(names,result+(True,'')):
                getattr(p,name).value=value
            if not result[13]:
                self.warning='UrbGEN IterativePlacement: target count not reached'
        except Exception as exc:
            p.IsValid.value=False
            p.ErrorMessage.value=str(exc)
            self.error='UrbGEN IterativePlacement: '+str(exc)
