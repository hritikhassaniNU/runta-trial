# Repo Doctor

Repo Doctor is the smallest experiment in the trial. The repository contains one intentional bug in `calculator.py` and a small pytest suite that makes the failure obvious.

I used it to establish a clean method before moving to larger systems:

1. prove the baseline is failing
2. prepare the runtime once
3. checkpoint that state
4. restore identical runs
5. let the agent make a change
6. validate with pytest and `git diff` independently of the agent

The simplicity is deliberate. With only one bug, platform behavior is easier to separate from application complexity.

See `ARCHITECTURE.md` for the Runta setup used around this repository.
