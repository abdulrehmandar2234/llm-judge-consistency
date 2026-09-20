"""The four ranking conditions the experiments compare.

Every condition is run `REPLICATES` times per job. Comparisons are always
between two conditions, or within one condition across its replicates:

    within  base                 -> run-to-run consistency      (experiment A)
    base vs shuffled             -> presentation-order effect   (experiment B)
    base vs temp07               -> temperature effect          (experiment C)
    base vs variant_b            -> prompt-phrasing effect      (experiment D)

`base` is the shared control, so it is the only condition that has to be
re-run when any single comparison changes.
"""

from dataclasses import dataclass

REPLICATES = 5


@dataclass(frozen=True)
class Condition:
    name: str
    prompt_variant: str
    temperature: float
    #: "canonical" presents candidates in data-file order every replicate.
    #: "shuffled" reshuffles per replicate from a seed derived from the
    #: replicate index, so the permutation is reproducible.
    order: str
    note: str


CONDITIONS = [
    Condition("base", "a", 0.0, "canonical",
              "control: prompt A, temperature 0, fixed candidate order"),
    Condition("shuffled", "a", 0.0, "shuffled",
              "prompt A, temperature 0, candidate order reshuffled per replicate"),
    Condition("temp07", "a", 0.7, "canonical",
              "prompt A, temperature 0.7, fixed candidate order"),
    Condition("variant_b", "b", 0.0, "canonical",
              "prompt B (reworded, same task), temperature 0, fixed order"),
]

BY_NAME = {c.name: c for c in CONDITIONS}

#: (label, condition_a, condition_b or None). None means "within-condition".
COMPARISONS = [
    ("A. Repeated identical runs", "base", None),
    ("B. Candidate order shuffled", "base", "shuffled"),
    ("C. Temperature 0.0 vs 0.7", "base", "temp07"),
    ("D. Prompt variant A vs B", "base", "variant_b"),
]
