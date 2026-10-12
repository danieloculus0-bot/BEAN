# Preregistered numerical reproducibility diagnostic (2026-10-12)

Status at registration: unrun. Diagnostic only. No fresh holdouts or learner optimization.

The raw-versus-annealed experiment on dedicated seeds 65–67 (run 38287851190) failed its prespecified identical-DQN-control condition for seed 66. First-candidate training frames and fitness matched but weight hashes differed at floating-point scales around 1e-7. This may reflect numerical backend differences; cause is unknown.

**Fixed experiment:** use previously observed seed 66 and the unchanged raw-branch learner blobs at source commit 59933e2beaebd8a5b86ec67a0516b85f808ae95e. Train exactly the first generation-0 candidate for 30 games, using the original seed multiset, and record final weights canonical SHA256, frames, updates, training trajectory summary, PyTorch version, CPU capability, and source SHA. Run two separate jobs each on Windows and Linux. No final validation or holdout games are accessed. No code modification, reward schedule tuning, hyperparameter search, or selection based on output.

Primary criterion: exact same-platform SHA256 and frames/updates across the two independent jobs. Secondary: compare SHA across platforms; different platforms need not be bitwise identical. Report failures and machine/software metadata. If exact hashes differ, do not reinterpret the original seed-66 result as confirmatory; investigate reproducibility in a separate, preregistered change. No Main merge, trading, hardware control, or claims of superiority.
