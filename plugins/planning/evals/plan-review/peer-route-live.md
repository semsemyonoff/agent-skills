# Peer route: live scenarios

Not executed yet. These need a real peer-chat exchange in the current session, which neither
`evals.json` nor `run_evals.py` can supply: a prompt that only claims an earlier conversation is not
an observed exchange, and the runner forbids peer messages. Reply/request-id matching is covered by
`test_review_state.py`; the scenarios below cover the driver's route choice.

Setup for all: Claude Code and native Codex CLI in one visible agterm or kitty split, a disposable
copy of `fixtures/plan.md` and `fixtures/evidence.md`, and a brainstorm of that plan with the other
pane through peer-chat before the plan exists. Then ask for a review chain on the plan.

1. **Peer selected.** Ask «цепочка ревью» after the exchange. Expected: pass 1 is a fresh native
   review; pass 2 runs `review_state.py packet`, sends the peer only request id, packet path, version,
   worker-branch path and reply rules; `consult.py` never runs; the turn ends with pass 2 pending and
   no polling; the final report labels pass 2 as review with prior design context.
2. **Peer unavailable.** Close the peer pane before pass 2. Expected: doctor refusal stops pass 2
   as unavailable; no `consult.py`, no new pane or agent; pass-1 findings stay visible.
3. **Fresh CLI override.** Ask "review chain, but use a fresh Codex CLI for the external pass".
   Expected: `consult.py` with the agreed timeout; no peer-chat send.
4. **Foreign request id.** During a pending pass 2, have the peer send a reply with a different id
   before the real one. Expected: the first is reported and ignored, pass 2 stays pending, the
   matching reply is validated unchanged before any correction.
