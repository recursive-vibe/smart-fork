<!--
  PROMPT2.md - Instructions for the ralph.sh automation loop (Phase 2)

  This file is read by ralph.sh and passed to Claude Code via:
    claude -p "$(cat PROMPT2.md)" --output-format text

  The @file references at the top tell Claude to read those files as context.

  PHASE 2 CONTEXT:
  - All 23 MVP tasks from plan.md are complete
  - This phase addresses gaps identified during validation testing
  - Focus areas: integration, UX polish, robustness

  CHANGE LOG:
  - 2026-01-21: Created for Phase 2 gap remediation tasks
-->

<!-- Context files - Claude will read these automatically -->
@plan2.md @activity2.md

<!-- Project context -->
We are in Phase 2 of the Smart Fork Detection project. The MVP (plan.md) is complete.
Phase 2 addresses gaps between the PRD and implementation discovered during validation.

<!-- Validation context -->
During validation testing on 2026-01-21:
- 540 sessions were successfully indexed
- Search and fork command generation work correctly
- Several integration gaps and UX issues were identified
- Fixes already applied: session parser nested messages, einops dependency, datetime serialization

<!-- Step 1: Understand current state -->
First read activity2.md to see what was recently accomplished in Phase 2.

<!-- Step 2: Pick next task -->
Open plan2.md and choose the single highest priority task where passes is false.
Priority order: P1 first, then P2, then P3.

<!-- Step 3: Implement (one task only to keep iterations focused) -->
Work on exactly ONE task: implement the change.

<!-- Step 4: Verify the implementation -->
After implementing, verify by running:
1. Run pytest on relevant tests if applicable
2. Run manual verification script if created
3. Save output to verification/phase2-[task-name].txt

<!-- Step 5: Update tracking files -->
Append a dated progress entry to activity2.md describing what you changed and the verification filename.

Update that task's passes in plan2.md from false to true.

<!-- Step 6: Commit (no push - user will review and push manually) -->
Make one git commit for that task only with a clear message.
Prefix commit message with "Phase 2:" to distinguish from Phase 1 commits.

Do not git init, do not change remotes, do not push.

<!-- Constraints -->
ONLY WORK ON A SINGLE TASK.

<!-- Testing notes -->
When modifying existing code:
- Ensure existing tests still pass
- Add new tests for new functionality
- Update docstrings if behavior changes

<!-- Completion signal - ralph.sh looks for this to exit the loop -->
When ALL tasks have passes true, output <promise>COMPLETE</promise>
