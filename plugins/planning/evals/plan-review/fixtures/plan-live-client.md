# Support bot reply threading

## Goal and scope
Replies sent by the support bot keep the original thread. Non-goals: the bot's transport, the ticket schema. The run must not message real chat accounts or contact the live chat provider.

## Acceptance criteria

### Executor acceptance
- The reply builder sets `thread_id` from the incoming message for text and attachment replies; a missing parent yields a new thread.

### Owner acceptance after run
- A reply sent through the live chat client lands in the original thread. Check: send a message to the staging bot from a test account and confirm the reply appears in that thread.

## Validation Commands
- `make test-reply` in `bot/`.

## Implementation Steps

### Task 1: Thread-aware reply builder
Files: `bot/reply.py`, `bot/tests/test_reply.py`.
Depends on: none.
- [ ] Set `thread_id` from the incoming message and cover the missing-parent case.
- [ ] Run `make test-reply`.
Acceptance: unit tests prove thread selection for text, attachment and missing parent.

### Task 2: Final verification
Files: `docs/bot.md`.
Depends on: Task 1.
- [ ] Verify every acceptance criterion.
- [ ] Run `make test` and `make lint` in `bot/`.

## Execution boundaries
Forbidden: any message to the live chat provider or real accounts.
