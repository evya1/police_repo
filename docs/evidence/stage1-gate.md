# Stage 1 Domain Gate Evidence

## Execution Details
- Date: 2026-08-21
- Test Suite: `tests/integration/test_local_two_agent_game.py`
- Environment: Python 3.14 / uv

## Verification Results

1. **Capture outcome**:
   - Command: `uv run pytest tests/integration/test_local_two_agent_game.py::test_stage1_capture_scores_20_5`
   - Result: PASSED. Verified outcome CAPTURE with scores Police=20, Thief=5.

2. **Survival outcome at threshold 35**:
   - Command: `uv run pytest tests/integration/test_local_two_agent_game.py::test_stage1_survival_at_step_35_scores_5_10`
   - Result: PASSED. Verified outcome SURVIVAL at step 35 with scores Police=5, Thief=10.

3. **Capture precedence at step 35**:
   - Command: `uv run pytest tests/integration/test_local_two_agent_game.py::test_stage1_capture_at_step_35_takes_precedence`
   - Result: PASSED. Capture at step 35 takes precedence over survival claim.

4. **Divergence refusal (OPEN-011)**:
   - Command: `uv run pytest tests/integration/test_local_two_agent_game.py::test_stage1_divergence_refusal`
   - Result: PASSED. Refuses to start when `max_moves` and `survival_threshold` diverge.

5. **Barrier quota enforcement**:
   - Command: `uv run pytest tests/integration/test_local_two_agent_game.py::test_stage1_barrier_quota_rejection`
   - Result: PASSED. Placing barriers beyond quota raises `IllegalMoveError` without corrupting state.

6. **Deterministic reproducibility**:
   - Command: `uv run pytest tests/integration/test_local_two_agent_game.py::test_stage1_deterministic_reproducibility`
   - Result: PASSED. Independent runs produce byte-identical move history and terminal states.
