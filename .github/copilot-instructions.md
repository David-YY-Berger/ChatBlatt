# Copilot Instructions — ChatBlatt

## Always consult the control docs first

Before working on anything touching the data model, population pipeline, or DB layer, read
`control_docs/README.md` and the specific doc(s) it points to for the area you're touching.
Don't re-derive context from scratch that's already written down there.

## Standing rules for every task

1. **Plan before implementing.** Gather the context you need, form a clear plan, and surface
   open questions — then confirm with the user in a focused way (one question at a time,
   concrete choices when possible) *before* writing code. If you notice an unrelated issue
   along the way, mention it rather than silently fixing or silently ignoring it.
2. **Keep `control_docs/` current — always, not just when asked.** After *any* code change
   (including a "just fix it" / bug-fix / review-driven change mid-task, not only
   feature work), check whether an existing doc covers the area you touched and update it
   in place — fix/restructure the existing content, don't just append more bullet points.
   Only add a new doc file when nothing existing fits (and list it in
   `control_docs/README.md`); only split/reorganize when a doc has grown unfocused. Docs
   should stay succinct, non-repetitive, and easy to find. Treat this as part of finishing
   the change, not a separate optional step.
3. **Check the whole inheritance chain before changing a shared method/attribute.** Before
   and after editing anything that's part of a class hierarchy — a base/abstract class
   method, a class-level attribute, a method with subclass overrides — search for every
   superclass *and* every subclass/implementer that touches it, not just the one file you
   started in. A change to a shared default, signature, or class attribute propagates via
   MRO/inheritance and can silently break a sibling subclass that relies on the old
   behavior (e.g. a class attribute one subclass needs re-set because a base class now sets
   it differently; an abstract method a sibling override implements with a different
   signature than the one you just assumed). If this search turns up an existing disparity
   — a subclass already out of sync with its base, a stub that silently no-ops instead of
   failing loudly, inconsistent overrides — mention it to the user, same as rule 1: don't
   silently fix it (unless it's the bug you were asked to fix) or silently ignore it.

## Project-specific safety note

This repo has no separate test database — every populator script writes to the one real
working DB. See `control_docs/conventions/safety_and_testing.md` before running, or asking
to run, anything that writes.
