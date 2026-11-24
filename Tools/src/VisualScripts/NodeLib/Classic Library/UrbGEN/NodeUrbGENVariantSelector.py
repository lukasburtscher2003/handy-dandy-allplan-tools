"""Choose reproducible collision-free variants from an already generated candidate pool.

Geometry remains in the native VS graph. BoundaryCheck and CollisionCheck supply
validated indexed boolean results. For each variant, candidates are considered in
seed-shuffled order, and greedily accepted until target count or exhaustion.
"""
import random
from NodeUtil import NodeBase

NodeBase.trace_node_name('NodeUrbGENVariantSelector')

def create_node(init_data):
    return NodeUrbGENVariantSelector(init_data)


def calculate_variantselector(candidate_count, inside_states, boundary_valid,
                              index_a, index_b, collision_states, collision_valid,
                              target_count, variant_count, base_seed, selected_variant):
    n = int(candidate_count)
    target = int(target_count)
    n_variants = int(variant_count)
    selected = int(selected_variant)
    if n < 0 or n > 2000:
        raise ValueError('CandidateCount must be between 0 and 2000')
    if target < 0 or target > n:
        raise ValueError('TargetCount must be between 0 and CandidateCount')
    if n_variants < 1 or n_variants > 100:
        raise ValueError('VariantCount must be between 1 and 100')
    if selected < 0 or selected >= n_variants:
        raise ValueError('SelectedVariant must be in 0..VariantCount-1')
    inside = list(inside_states)
    boundary_ok = list(boundary_valid)
    aa = list(index_a); bb = list(index_b)
    hits = list(collision_states); collision_ok = list(collision_valid)
    if len(inside) != n or len(boundary_ok) != n:
        raise ValueError('InsideStates and BoundaryValid must each have CandidateCount entries')
    expected = n * (n - 1) // 2
    if not (len(aa) == len(bb) == len(hits) == len(collision_ok) == expected):
        raise ValueError('All pairwise lists need N*(N-1)/2 entries')
    if not all(bool(v) for v in boundary_ok) or not all(bool(v) for v in collision_ok):
        # Fail-closed; Never show unvalidated candidates as collision-free.
        return ([False] * n, [], [0] * n_variants, [False] * n_variants,
                [int(base_seed) + v for v in range(n_variants)], 0, False, 'Invalid boundary/collision geometry results')
    colliding = [set() for _ in range(n)]
    seen = set()
    for a, b, collision in zip(aa, bb, hits):
        a = int(a); b = int(b)
        if not (0 <= a < b < n) or (a, b) in seen:
            raise ValueError('Invalid or duplicate pair (%s, %s)' % (a, b))
        seen.add((a,b))
        if bool(collision):
            colliding[a].add(b); colliding[b].add(a)
    if len(seen) != expected:
        raise ValueError('Missing pairwise collision results')
    variants = []
    seeds = []
    counts = []
    complete = []
    for v in range(n_variants):
        seed = int(base_seed) + v
        seeds.append(seed)
        order = list(range(n))
        random.Random(seed).shuffle(order)
        accepted = []
        accepted_set = set()
        for i in order:
            if len(accepted) >= target: break
            if not bool(inside[i]): continue
            if colliding[i].isdisjoint(accepted_set):
                accepted.append(i)
                accepted_set.add(i)
        variants.append(accepted)
        counts.append(len(accepted))
        complete.append(len(accepted) == target)
    chosen = variants[selected]
    mask = [i in set(chosen) for i in range(n)]
    return mask, chosen, counts, complete, seeds, len(chosen), True, ''


class NodeUrbGENVariantSelector(NodeBase):
    def _create_output(self):
        p = self.build_ele
        output_names = ('KeepStates','SelectedIndices','VariantCounts','VariantComplete',
                        'VariantSeeds','SelectedCount','IsValid','ErrorMessage')
        for name in output_names:
            self._set_init_node_output(getattr(p,name))
        try:
            result = calculate_variantselector(
                p.CandidateCount.value, p.InsideStates.value, p.BoundaryValid.value,
                p.IndexA.value, p.IndexB.value, p.CollisionStates.value,
                p.CollisionValid.value, p.TargetCount.value, p.VariantCount.value,
                p.BaseSeed.value, p.SelectedVariant.value)
            for name, value in zip(output_names, result):
                getattr(p,name).value = value
        except Exception as exc:
            self.error = 'UrbGEN VariantSelector: ' + str(exc)
