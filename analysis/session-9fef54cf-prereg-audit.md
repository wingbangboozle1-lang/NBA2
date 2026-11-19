# Pre-registration and tamper-evidence audit — session `arena/9fef54cf-nba2` (2026-11-19 UTC)

**Scope.** Checks two brief items against the repository's own history: (a) "freeze a pre-registration file per strategy before its first bet" and (b) "tamper-evident ledger: hash each pick, publish the hash before tip, verify after settlement". Read-only. Nothing was re-frozen, re-hashed, repaired, or deleted. Frozen files that were changed are reported, not silently fixed.

**Reproduce.** `python3 audit/9fef54cf/prereg_audit.py` (run from the repo root, on a full clone). Output: `audit/9fef54cf/prereg_audit.json`. Every commit link below resolves on GitHub (`https://github.com/wingbangboozle1-lang/NBA2/commit/<sha>`).

**Source class.** This audit uses repository evidence only: committed files and git commit timestamps. It does **not** use or re-check any NBA.com value, so no official NBA source is cited for these rows. Official sources were not re-read in this session. The NBA finals dates used for ordering are the repo's own committed `data/raw/finals_*.json` files, and their commit links are given.

**Clone note.** The sandbox clone was shallow (grafted at `41cfd81`). It was unshallowed before the audit, so the timeline uses the full `origin/main` history (585 commits). Every "on main" flag below is an ancestry check against `origin/main`.

---

## 1. Verdict

| Brief item | Verdict | One-line reason |
|---|---|---|
| Tamper-evident ledger, sealed picks | **Partly holds.** Pick content is tamper-evident. The seal *time* is not. | Both sealed digests recompute exactly, but the `sealed_at_utc` header differs between git versions of the 11/14 file, and the hash rule does not cover it. |
| Publish hash before tip | **Holds on repo evidence only.** | All 49 sealed picks were committed before their tip time. Git commit times are author-set, so this is not independent proof of publication time. |
| Pre-registration per strategy, frozen before first bet | **Does not hold.** | The freeze was written after the outcomes it governs existed, was re-stamped at each re-cut, and the strategy IDs refer to different strategies in different files. |
| Pre-registration hashes verifiable | **Does not hold.** | v2: none of the 7 stored hashes match the file under any of 4 tested rules. v3: 8 of 9 match canonical JSON; S9 matches nothing. |

---

## 2. Findings

Severity: **H** = invalidates a stated guarantee, **M** = weakens it, **L** = cosmetic or documentation.

### F-PR-01 (H) — The v2 pre-registration was re-stamped each time the data was re-cut

`data/v2/preregistration.json` and `data/v2/prereg/S1–S7.json` have a `frozen_at_utc` that changes from version to version. The signal, thresholds, universe, and settlement rule do **not** change. Only the timestamp, `frozen_by`, and `prereg_hash` change. The S1 history:

| Commit | Committed (UTC) | On `origin/main` | `frozen_at_utc` declared | `frozen_by` | Declared minus commit |
|---|---|---|---|---|---|
| [e4a2f47](https://github.com/wingbangboozle1-lang/NBA2/commit/e4a2f47) | 2026-11-15 12:51 | yes | 2026-11-15 12:00 | arena/98b0eae9-nba2 | −51 min |
| [8086173](https://github.com/wingbangboozle1-lang/NBA2/commit/8086173) | 2026-11-16 00:16 | no (branch) | 2026-11-15 11:45 | arena/04a61ac0-nba2 | −751 min |
| [b777098](https://github.com/wingbangboozle1-lang/NBA2/commit/b777098) | 2026-11-16 18:28 | no (branch) | 2026-11-15 12:00 | arena/98b0eae9-nba2 | −1828 min |
| [6a00f61](https://github.com/wingbangboozle1-lang/NBA2/commit/6a00f61) | 2026-11-17 16:10 | no (branch) | 2026-11-17 15:12 | arena/45f14c5c-nba2 | −58 min |
| [7accb28](https://github.com/wingbangboozle1-lang/NBA2/commit/7accb28) | 2026-11-19 06:37 | no (branch `arena/fb1d73b2-nba2`) | 2026-11-19 06:20 | arena/fb1d73b2-nba2 | −17 min |

A freeze timestamp that is rewritten to the current time at each re-cut shows nothing about when the rules were fixed. Where the declared time is *earlier* than the commit (the 11/15 11:45 version), the claim is also unverifiable from the repo alone.

### F-PR-02 (H) — The v2 freeze postdates the outcomes it governs

- The strategy lab that defines and evaluates S1–S7 was first committed 2026-11-14 11:26 UTC ([e9ece24](https://github.com/wingbangboozle1-lang/NBA2/commit/e9ece24)). The file's meta says it covers 2026-10-23 → 2026-11-14 (172 scored games).
- Official finals for 11/13 were committed 2026-11-14 10:25 UTC ([13aa58f](https://github.com/wingbangboozle1-lang/NBA2/commit/13aa58f)). Finals for 11/14 were committed 2026-11-15 11:58 UTC ([2b32dcd](https://github.com/wingbangboozle1-lang/NBA2/commit/2b32dcd)), **two minutes before the claimed 12:00 UTC freeze** and 53 minutes before the freeze commit.
- The v2 pre-registration first reached `main` at [e4a2f47](https://github.com/wingbangboozle1-lang/NBA2/commit/e4a2f47) (2026-11-15 12:51 UTC). That commit also adds `data/v2/strategy_lab.json` (the evaluated results), so the rules and their in-sample results were introduced together.

So the rules were registered after the 11/13 and 11/14 results were committed and were stored alongside results computed on those same games. The leakage rule in the lab (`no look-ahead detected`) only covers ratings, not the choice of rules. This is hindsight, not pre-registration.

### F-PR-03 (H) — Strategy IDs S1–S7 are not the same strategies across files

The same ID names three different strategy sets:

| ID | Strategy lab (evaluated, [e9ece24](https://github.com/wingbangboozle1-lang/NBA2/commit/e9ece24)) | v2 pre-registration (frozen) | v3 pre-registration |
|---|---|---|---|
| S1 | Model side (moneyline, all games) | Consensus-rating side | Estimator-agreement moneyline |
| S2 | Model total vs league average | Total mean-reversion | Disagreement-fade spread |
| S3 | Model side, \|margin\| ≥ 5 pts | Two-leg cross-game parlay | Possession-model total |
| S4 | Road side when model fades home by 3+ | Same-game spread+total | Rotation-availability fade |
| S5 | Same-game parlay: side + total | Player prop (pts/reb/ast) | Same-game parlay: spread + total |
| S6 | Cross-game parlay: two model sides | Prop combo (pts+reb) | Availability-blind guardrail fade |
| S7 | Player prop / prop combo | Injury-availability fade | Schedule-spot fade |
| S8 | — | — | Player-prop minutes model |
| S9 | — | — | Ledger-only champion |

A pre-registration is only meaningful if it names the strategy that is graded. Here the frozen S1 is not the S1 whose results are on the page. The leaderboard therefore cannot be tied to any frozen rule.

### F-PR-04 (H) — The v3 pre-registration was overwritten in place and rolled forward

`data/v3/prereg/S1–S9` were committed on 2026-11-15 with a 3-day window 11/15 → 11/18 and `registered_at_utc` 11:41 UTC ([bbade89](https://github.com/wingbangboozle1-lang/NBA2/commit/bbade89), 12:03 UTC commit). They were then rewritten twice:

| Commit | Committed (UTC) | On main | Window | `registered_at_utc` declared | Declared minus commit |
|---|---|---|---|---|---|
| [bbade89](https://github.com/wingbangboozle1-lang/NBA2/commit/bbade89) | 2026-11-15 12:03 | yes | 11/15 → 11/18 | 2026-11-15 11:41 | −23 min |
| [4a5e930](https://github.com/wingbangboozle1-lang/NBA2/commit/4a5e930) | 2026-11-16 02:34 | no (branch) | 11/16 → 11/19 | 2026-11-16 02:45 | **+10 min** |
| [fde5a90](https://github.com/wingbangboozle1-lang/NBA2/commit/fde5a90) | 2026-11-17 16:43 | yes | 11/17 → 11/20 | 2026-11-17 17:05 | **+21 min** |

The window moves forward by one day each time, which means the universe of games was redefined after the outcomes of the games dropped from the window were known. The declared registration time is later than the commit that wrote it, so the file describes a registration that did not yet exist when the commit was made. Across these versions the only fields that changed are `window`, `registered_at_utc`, `registered_by`, and `sha256`. The strategy name, signal, thresholds, universe, and settlement rule are unchanged, so the registration was re-dated rather than revised.

Also in v3: [7459b70](https://github.com/wingbangboozle1-lang/NBA2/commit/7459b70) (2026-11-16 02:38 UTC) describes "pre-registration files for all 9 strategies". S8 and S9 exist only here, and neither appears in the strategy lab.

### F-PR-05 (H) — Hash verification fails for v2 and for S9 in v3

Checked with `audit/9fef54cf/prereg_audit.py`:

- **v2 (7 of 7 fail).** `prereg_hash` does not equal the SHA-256 of the file's raw bytes, of its canonical JSON with or without the hash field, or of canonical JSON without `frozen_at_utc`. The rule is not stated in `data/v2/preregistration.json`, which only says "each file hashed". **The published hashes cannot be reproduced.**
- **v3 (8 of 9 pass).** S1–S8 match the SHA-256 of canonical JSON (sorted keys, compact separators, excluding the `sha256` field). The rule is not written in the files. **S9 fails in every version**, including its first commit [7459b70](https://github.com/wingbangboozle1-lang/NBA2/commit/7459b70), so its hash never matched.

### F-PR-06 (M) — The sealed 11/14 ledger's seal time is not covered by its hash

`data/raw/ledger/sealed-2026-11-14.json` has an identical `predictions` array (digest `c841e8f3…`) in all six commits that touched it, so the pick content is intact. The header is not:

| Commit | On main | `header.sealed_at_utc` |
|---|---|---|
| [b4cb4b7](https://github.com/wingbangboozle1-lang/NBA2/commit/b4cb4b7) | yes | 2026-11-14 00:58:54 |
| [7227a97](https://github.com/wingbangboozle1-lang/NBA2/commit/7227a97) | **no (branch `arena/79e87c81-nba2`)** | **2026-11-14 00:49:16** |
| [0d79541](https://github.com/wingbangboozle1-lang/NBA2/commit/0d79541) | yes | 2026-11-14 00:58:54 |
| [8783ef6](https://github.com/wingbangboozle1-lang/NBA2/commit/8783ef6) | yes | 2026-11-14 00:58:54 |
| [cb3b7f1](https://github.com/wingbangboozle1-lang/NBA2/commit/cb3b7f1) | yes | 2026-11-14 00:58:54 |
| [41cfd81](https://github.com/wingbangboozle1-lang/NBA2/commit/41cfd81) (main HEAD at audit start) | yes | 2026-11-14 00:58:54 |

The note in the header also changes between 00:58 and 00:49. The `hash_rule` says "sha256 over canonical JSON of the predictions array", so the timestamp is not covered and can change without breaking the digest. The file on main says 00:58:54. The 00:49:16 value appears only on a branch, so the repo does not show which seal time was real.

### F-PR-07 (M) — The sealed 11/13 and 11/14 ledgers verify, and were committed before tip

- `sealed-2026-11-13.json`: 22 picks, digest recomputes ✔ (`cf7dedc6…`), one content version on main, first committed [da55ac4](https://github.com/wingbangboozle1-lang/NBA2/commit/da55ac4) at 22:56:51 UTC, 5 minutes after the header's `sealed_at_utc` (22:51:54).
- `sealed-2026-11-14.json`: 27 picks, digest recomputes ✔ (`c841e8f3…`), first committed [b4cb4b7](https://github.com/wingbangboozle1-lang/NBA2/commit/b4cb4b7) at 01:03:50 UTC, 4.9 minutes after the seal time.
- All 49 picks were committed before their ET tip time (ET converted to UTC with `zoneinfo`).

Limits: git commit timestamps are set by the committer and can be faked. These are not evidence of when the hash was published to a third party. Publication needs an external anchor (see suggestions).

### F-PR-08 (L) — Two session claims are on the board for the same registry

Branch `arena/fb1d73b2-nba2` (commit [7accb28](https://github.com/wingbangboozle1-lang/NBA2/commit/7accb28), claim [78c4243](https://github.com/wingbangboozle1-lang/NBA2/commit/78c4243)) re-freezes v2 on 2026-11-19. It is unmerged. If it merges as written, F-PR-01 repeats. Logged as a request on the board (RQ-9F-1), not edited here.

### F-PR-09 (L) — Claimed freeze hashes are not in any PR body or board entry

The hashes in `data/v2/preregistration.json` and in `sha256` fields are not cross-referenced in `COORDINATION.md` or any PR description, so a reviewer cannot check a published hash against an independent record.

---

## 3. What holds

- Sealed ledgers verify under their own stated rule (both files).
- The 11/13 sealed content has not changed since its first commit.
- All 49 sealed picks are committed before their tips (repo-timestamp evidence only).
- The pick sets are "injury-blind" (every row `injury_blind: true`) and carry `sealed_before_tip: true`, which matches the sealing rule.
- v3 S1–S8 hashes match their current content under canonical JSON.

---

## 4. Suggestions (not implemented — owner decision needed)

Each suggestion is listed with what it would change and what it would not touch. None has been implemented.

| # | Suggestion | Effect | Needs |
|---|---|---|---|
| S-PR-1 | **Never re-stamp a freeze.** Any change to a strategy creates a new versioned ID (e.g., `S1-v2`, `S1-v3`) with its own file, and the old file is kept. The manifest is append-only. | Makes the freeze history auditable | Owner approval of the policy |
| S-PR-2 | **Declare one hash rule in each file and check it in CI.** E.g., "sha256 of canonical JSON of the file minus the `hash` field". The checker fails the build on mismatch. | Makes hashes reproducible | Choose the rule; decide whether to re-hash v2 (which is a new registration, not a repair) |
| S-PR-3 | **Put the seal time inside the hashed payload** (or in a separately hashed header). | Closes F-PR-06 | Owner approval; a new seal format for future ledgers only |
| S-PR-4 | **Anchor each seal digest outside the repo before tip** — e.g., a signed git tag pushed before tip, or an OpenTimestamps proof. | Turns "committed before tip" into independent evidence | Choose the anchor and who runs it |
| S-PR-5 | **Relabel every v2/v3 strategy as "retro-specified, not pre-registered"** on the Pre-registration and Leaderboard pages, and show each registration's first-freeze date next to the outcome dates it followed. | Honest status, no change to numbers | Owner approval of the wording |
| S-PR-6 | **Make the first real pre-registration prospective**: freeze a single strategy with ID, rule, universe, threshold, and settlement rule, committed before the first tip of the next slate, with the digest anchored per S-PR-4. | First genuinely pre-registered test | Owner picks the strategy and approves the thresholds (R-048) |
| S-PR-7 | **Add a CI gate** that fails if any file in `data/*/prereg/` or `data/raw/ledger/` changes after its first commit, unless a new ID is created. | Stops future in-place edits | Owner approval |

---

## 5. Questions the owner must answer

1. Which strategy set is the official one: the strategy lab's S1–S7, the v2 pre-registration's S1–S7, or the v3 set S1–S9? (F-PR-03)
2. Should the v2 and v3 registrations be kept as "retro-specified" (S-PR-5), or withdrawn from the leaderboard until a prospective one exists?
3. Which anchor for pre-tip publication: signed tag, OpenTimestamps, or a third-party timestamp? (S-PR-4)
4. Which of the hash rules in S-PR-2 is the canonical one? (Current files use two rules; v2 uses none that matches.)
5. Is the 00:49:16 or the 00:58:54 seal time for the 11/14 ledger the real one? (F-PR-06; only the owner, using an external record, can settle this.)
6. Approve S-PR-1 and S-PR-7 as repository policy?

---

## 6. Flagged for Review (for the integration session to publish)

These items are not published here, because the site and its navigation are integration-owned. The integration session should mirror them to the Flagged for Review page with the links above.

| Flag | Item | Links |
|---|---|---|
| FR-PR-01 | v2 pre-registration re-stamped 4 times; freeze timestamp not evidence | F-PR-01 commits above |
| FR-PR-02 | v2 freeze postdates 11/13 and 11/14 official finals committed to the repo | [13aa58f](https://github.com/wingbangboozle1-lang/NBA2/commit/13aa58f), [2b32dcd](https://github.com/wingbangboozle1-lang/NBA2/commit/2b32dcd), [e4a2f47](https://github.com/wingbangboozle1-lang/NBA2/commit/e4a2f47) |
| FR-PR-03 | Strategy IDs S1–S7 differ across lab, v2 prereg, and v3 prereg | [e9ece24](https://github.com/wingbangboozle1-lang/NBA2/commit/e9ece24), [e4a2f47](https://github.com/wingbangboozle1-lang/NBA2/commit/e4a2f47), [bbade89](https://github.com/wingbangboozle1-lang/NBA2/commit/bbade89) |
| FR-PR-04 | v3 pre-registration rewritten in place; window rolled 11/15→11/16→11/17; declared times later than commits | [bbade89](https://github.com/wingbangboozle1-lang/NBA2/commit/bbade89), [4a5e930](https://github.com/wingbangboozle1-lang/NBA2/commit/4a5e930), [fde5a90](https://github.com/wingbangboozle1-lang/NBA2/commit/fde5a90) |
| FR-PR-05 | Published prereg hashes do not reproduce (v2 all 7; v3 S9) | `audit/9fef54cf/prereg_audit.json` |
| FR-PR-06 | Sealed 11/14 seal time varies between versions and is not covered by the hash | [b4cb4b7](https://github.com/wingbangboozle1-lang/NBA2/commit/b4cb4b7), [7227a97](https://github.com/wingbangboozle1-lang/NBA2/commit/7227a97) |

---

## 7. Method and limits

- Commands: `git log --all --full-history` per file for every version; `git show <sha>:<path>` for content; `git merge-base --is-ancestor <sha> origin/main` for main membership; SHA-256 per the candidate rules listed in the JSON.
- Full output: `audit/9fef54cf/prereg_audit.json` (generated from the commit at `HEAD` of this branch).
- Not verified: whether any strategy was actually bet on; whether the seal digests were published anywhere outside git; the validity of any NBA official value. No official NBA source was fetched.
- Commit timestamps are the committer dates recorded by git. They are evidence of ordering inside this repo, not of external publication.
