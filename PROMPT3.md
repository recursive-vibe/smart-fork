<!--
  PROMPT3.md - Instructions for the ralph.sh automation loop (Phase 3)

  This file is read by ralph3.sh and passed to Claude Code via:
    claude -p "$(cat PROMPT3.md)" --output-format text

  The @file references at the top tell Claude to read those files as context.

  PHASE 3 CONTEXT:
  - All 23 MVP tasks from plan.md are complete
  - All 11 gap remediation tasks from plan2.md are complete
  - This phase focuses on enhancements: performance, UX, intelligence features

  CHANGE LOG:
  - 2026-01-21: Created for Phase 3 feature development
-->

<!-- Context files - Claude will read these automatically -->
@plan3.md @activity3.md

<!-- Project context -->
We are in Phase 3 of the Smart Fork Detection project. MVP (plan.md) and gap remediation (plan2.md) are complete.
Phase 3 focuses on performance optimizations, UX enhancements, and intelligent features.

<!-- Current state -->
As of Phase 2 completion:
- 540+ sessions indexed and searchable
- MCP tools working: fork-detect, get-session-preview
- Background indexing operational
- Progress display, timeout handling, error states all implemented

<!-- Step 1: Understand current state -->
First read activity3.md to see what was recently accomplished in Phase 3.

<!-- Step 2: Pick next task -->
Open plan3.md and choose the single highest priority task where passes is false.
Priority order: P1 first, then P2, then P3.

<!-- Step 3: Implement (one task only to keep iterations focused) -->
Work on exactly ONE task: implement the change.

<!-- Step 4: Verify the implementation -->
After implementing, verify by:
1. Run pytest on relevant tests if applicable
2. Add new tests for new functionality
3. Run manual verification if needed
4. Save verification output to verification/phase3-[task-name].txt

<!-- Step 5: Update tracking files -->
Append a dated progress entry to activity3.md describing what you changed and verification results.

Update that task's passes in plan3.md from false to true.

<!-- Step 6: Commit (no push - user will review and push manually) -->
Make one git commit for that task only with a clear message.
Prefix commit message with "Phase 3:" to distinguish from earlier phases.

Do not git init, do not change remotes, do not push.

<!-- Constraints -->
ONLY WORK ON A SINGLE TASK.

<!-- Testing notes -->
When adding new features:
- Add comprehensive tests for new functionality
- Ensure existing tests still pass
- Update docstrings and type hints
- Consider backwards compatibility

<!-- Completion signal - ralph3.sh looks for this to exit the loop -->
When ALL tasks have passes true, output <promise>COMPLETE</promise>
