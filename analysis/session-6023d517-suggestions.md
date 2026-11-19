# Suggestions — to be reviewed and chosen before anything is implemented

Nothing in this list has been built. Each is a proposal with its cost, its blocker and what
would make it worth doing. The queue exists so a decision can be made **before** code is
written, not after.

## Tier 1 — unblocks the most, costs the least

| ID | Suggestion | Why | Cost | Blocker | Worth it when |
|---|---|---|---|---|---|
| SG-V7-01 | **Connect a closing-line feed** | Every "edge" on the site is uncomputable without it. It is the single input that turns a projection into a decision | A subscription or a licensed vendor | Money / legal | Immediately — nothing else moves the needle as far |
| SG-V7-02 | **Read and archive the injury report daily** | Turns the availability column from an empty promise into an input, and makes S-08 evaluable | ~10 min/day, automatable | An egress path that reaches `official.nba.com` from CI (it does: 200 on the runner probe) | Immediately |
| SG-V7-03 | **Publish the luck z at three exponents** | Q9 is cheap to answer and it decides whether the luck gate is real or an artefact of 13.91 | Hours | None | As soon as someone asks whether luck is real |
| SG-V7-04 | **Move the pre-registration hash into a git tag** | The hash is in a file the same commit can change. A tag on the commit that froze the picks is tamper-evident in a way a file is not | Hours | None | Before the first real stake |

## Tier 2 — improves the model's honesty

| ID | Suggestion | Why | Cost | Blocker |
|---|---|---|---|---|
| SG-V7-05 | **Per-market ρ, not one ρ** | Spread×total is one pair. Spread×spread across games, and player-line×team-total, are the pairs people actually stack | Days | A larger finals sample |
| SG-V7-06 | **Publish a calibration plot, not just log-loss** | Log-loss says whether the probabilities are useful; calibration says *where* they are wrong, which is what a re-cut needs | Days | None |
| SG-V7-07 | **Score the model on ATS decisions, not just winners** | The published spread is the thing a reader would use; scoring the moneyline tests a different model | Days | None |
| SG-V7-08 | **Report the disagreement's own predictive value** | The site claims the disagreement is the confidence signal. That claim is currently untested — a large gap should mean a worse prediction, and that is measurable | Days | None |

## Tier 3 — site and decision support

| ID | Suggestion | Why | Cost |
|---|---|---|---|
| SG-V7-09 | **A single "what changed since yesterday" page** | The tree has 58 pages; a reader cannot see the delta. One page diffing the last two snapshots would be the most-read page on the site | Days |
| SG-V7-10 | **Retire or archive the v1/v3/v4/v5 trees under `archive/`** | Five generators publish five dashboards. README already says only `site/` is published; making that structural would remove the confusion at its root | Days, mostly review |
| SG-V7-11 | **One nav generator** | Every layer appends to the sidebar; v6 groups it; v7 appends after grouping. Each new layer adds a new failure mode. One generator with a registry would end it | Days |
| SG-V7-12 | **Fix the GitHub Pages source** | Measured: Pages is `build_type: legacy`, source `main /`, so `/NBA2/` serves the root pointer, not `site/`. Flipping Settings → Pages → Source to GitHub Actions is one owner action | Minutes, needs owner |

## What I would implement first, if asked

**SG-V7-01 and SG-V7-02.** Without a price and an availability feed, this is a very careful
description of a model that cannot be acted on. With them, every gate on the site starts
returning a number that matters instead of a BLOCKED.
