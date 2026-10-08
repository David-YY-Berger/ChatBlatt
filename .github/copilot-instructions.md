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

## Project-specific safety note

This repo has no separate test database — every populator script writes to the one real
working DB. See `control_docs/conventions/safety_and_testing.md` before running, or asking
to run, anything that writes.
