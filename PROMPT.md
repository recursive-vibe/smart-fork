@plan.md @activity.md

We are rebuilding the project from scratch in this repo.

First read activity.md to see what was recently accomplished.

Start the server locally with `python -m smart_fork.server`. If port is taken, try another port.

Open plan.md and choose the single highest priority task where passes is false.

Work on exactly ONE task: implement the change.

After implementing, verify by running:
1. Run pytest on relevant tests
2. Save output to verification/[task-name].txt

Append a dated progress entry to activity.md describing what you changed and the verification filename.

Update that task's passes in plan.md from false to true.

Make one git commit for that task only with a clear message.

Do not git init, do not change remotes, do not push.

ONLY WORK ON A SINGLE TASK.

When ALL tasks have passes true, output <promise>COMPLETE</promise>
