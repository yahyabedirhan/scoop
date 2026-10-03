# Handoff: icon legibility effort

You are the orchestrator for the `icon-legibility` effort. Build it from its
spec and tickets and deliver one pull request that shows five icon prototypes
for the maintainer to review.

## Where the work lives

- Worktree `/Users/yahyabedirhanpak/.treehouse/scoop-abb122/1/scoop`, branch
  `feat/icon-legibility`, leased from `treehouse` with holder `icon-legibility`
  and lease id `caf583f5d54e716116122f2dedeaed1b`.
- Spec: `.specs/05-icon-legibility.md`, published as the GitHub issue "Spec: icon
  legibility" (#31).
- Tickets, sub-issues of the spec with native blocking links, label
  `effort:icon-legibility`:
  - "Prototype the Scale-up icon variant with its review sheet" (#32), no blockers.
  - "Prototype the Tight diagonal and Spoon-led icon variants" (#33), blocked by #32.
  - "Prototype the Heavy and Compact glyph icon variants" (#34), blocked by #32.
  - "Ship the picked icon variant" (#35), `needs-info`. It waits on the
    maintainer's pick at PR review, so do not build it now.

## Settled with the maintainer

These came from a grilling session and are not in the spec in these words.

- The maintainer likes the spoon-pointer concept. The complaint is that at
  toolbar size the shapes are tiny and their meaning is lost. This is a
  redesign that keeps the concept and its actors, not a pixel scale-up. A
  bolder, cartoon-like treatment is welcome.
- Use the user-level `logo-design` skill for the design work. The maintainer
  asked for it by name.
- Both the extension icons and the README logos change, and they should look
  similar in size. The small cut may be simpler so it reads at 16 px, and the
  README logo may be more balanced. They must stay recognisably one mark.
- The maintainer does not care about pixel mechanics. Settle those yourself.
- The maintainer reviews the five prototypes in the PR itself, so the PR
  description must embed the review images.
- A new patch release follows once the pick is shipped. It is not part of this PR.

## Open questions

The maintainer asked not to be asked anything more while this is built. Do not
message the session that handed over. Decide open questions yourself and list
them, with your choice, in the PR description.

## State of the repo

- `main` is at `ba4f5c5 feat: ship the icon as green on a white tile`, the
  shipped green-on-white icon this effort improves.
- The previous icon effort's handoffs are in `.handoff/2026-10-0*-icon-redesign*.md`
  and its record is `.specs/04-icon-redesign.md`. Its rejected motifs must not
  return.
- In that effort the generator already supported `--variant` choices with
  512 px previews, and the PR showed them. Git history around PR #15 has that
  code if it helps.

## Suggested skills

- `orchestrate-effort` to run the effort and deliver the PR.
- `logo-design` for every prototype, including its 16 px, one-colour and
  reversed tests and its audit and test-sheet scripts.
- `implement` and `tdd` for the delegated tickets.
- `to-pr` to write the PR description.
