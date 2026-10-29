"""Evidence-gap advisor: tells the merchant which missing evidence would most raise win likelihood."""
from __future__ import annotations
from dataclasses import dataclass, replace

from .models import Dispute
from .playbooks import PLAYBOOKS, win_likelihood, _has


@dataclass
class Gap:
    field: str
    gain: float
    why: str


def evidence_gaps(d: Dispute) -> list[Gap]:
    """Missing positive-weight evidence for this reason code, ranked by marginal win-likelihood gain."""
    base = win_likelihood(d)
    gaps: list[Gap] = []
    for key, w, txt in PLAYBOOKS[d.reason]:
        if w <= 0 or _has(d.evidence, key):
            continue
        val = ["(collected)"] if isinstance(getattr(d.evidence, key), list) else True
        ev2 = replace(d.evidence, **{key: val})
        gain = round(win_likelihood(replace(d, evidence=ev2)) - base, 2)
        if gain > 0:
            gaps.append(Gap(key, gain, txt))
    return sorted(gaps, key=lambda g: (-g.gain, g.field))


def flips_to_contest(d: Dispute, threshold: float = 0.5) -> list[str]:
    """Single missing evidence items that alone would move the recommendation from accept to contest."""
    base = win_likelihood(d)
    if base >= threshold:
        return []
    return [g.field for g in evidence_gaps(d) if base + g.gain >= threshold]


def report(disputes: list[Dispute]) -> str:
    lines = ["| dispute | reason | win now | top missing evidence | gain | flips to contest |", "|---|---|---|---|---|---|"]
    for d in disputes:
        gaps = evidence_gaps(d)
        top = gaps[0] if gaps else None
        lines.append(
            f"| {d.id} | {d.reason.value} | {win_likelihood(d):.2f} | {top.field if top else '-'} | "
            f"{f'+{top.gain:.2f}' if top else '-'} | {', '.join(flips_to_contest(d)) or '-'} |"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    from .seed import SEED
    print(report(SEED))
