import random

from polyfix.geometry.layout import Layout
from polyfix.geometry.ortho import FancyOrthoDomain


def select_indices(n: int, fraction: float, seed: int) -> set[int]:
    k = round(fraction * n)
    return set(random.Random(seed).sample(range(n), k))


def shrink_domain(domain: FancyOrthoDomain, factor: float) -> FancyOrthoDomain:
    c = domain.centroid
    s = 1 - factor
    coords = [(c.x + (p.x - c.x) * s, c.y + (p.y - c.y) * s) for p in domain.coords]
    return FancyOrthoDomain.from_tuple_list(coords, domain.name)


def perturb_layout(layout: Layout, fraction: float, factor: float, seed: int) -> Layout:
    chosen = select_indices(len(layout.domains), fraction, seed)
    domains = [
        shrink_domain(d, factor) if i in chosen else d
        for i, d in enumerate(layout.domains)
    ]
    return Layout(domains)
