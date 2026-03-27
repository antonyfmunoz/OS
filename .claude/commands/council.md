# Council Mode — Multi-Agent Problem Solving

Run multiple Claude Code agents on the
same problem independently, then
synthesize the best solution.

## When to use
Complex decisions with multiple valid
approaches. Architecture choices.
Debugging hard problems.
Any decision worth multiple perspectives.

## Process
1. Commit current state to main
2. Create N branches:
   git checkout -b council/perspective-1
   git checkout -b council/perspective-2
   git checkout -b council/perspective-3

3. In each branch run:
   claude -p "Solve [problem].
   Do not look at other branches.
   Produce your best solution."

4. Review all solutions:
   git diff council/perspective-1 council/perspective-2

5. Synthesize on main:
   claude -p "Review these N solutions
   [paste each]. Build the best
   combined approach."

## Notes
Each agent works in isolation.
Disagreement between agents = complex problem.
Agreement between agents = high confidence.
