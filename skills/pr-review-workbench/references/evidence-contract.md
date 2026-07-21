# Evidence and Cognitive-Load Contract

## Decision states

- `ready for human decision`: every required dataset is complete, the captured
  head SHA is stable, and checks contain no known blocker. This does not mean
  correct, safe, or approved.
- `not ready`: evidence is partial, forbidden, unsupported, stale, failed, or
  otherwise insufficient.

Unknown evidence always fails closed. Refresh at generation, explicit refresh,
and immediately before a review action. A refresh cannot make reading and
mutation atomic; the action therefore revalidates the immutable head SHA.

## Dataset states

Use only `complete`, `partial`, `forbidden`, `unsupported`, and `stale`. Record
state per dataset rather than hiding one failed query inside an overall success.

## Claim states

Every behavioral claim has:

- a one-sentence claim;
- a user/system impact;
- one or more source anchors when available;
- a proof state using the dataset vocabulary;
- the smallest remaining question when it is not complete.

Receipts, summaries, screenshots, and model confidence are context, not proof.

## First-screen budget

At 1440x900, without scrolling, render exactly one decision state, no more than
five primary facts, and exactly one next action. Prefer:

1. decision state;
2. highest-impact behavioral change or evidence blocker;
3. scope size;
4. check/proof condition;
5. immutable head SHA.

The next action should open the highest-impact or blocking evidence. File churn,
secondary checks, and raw detail belong behind drill-down.

## Safety

Treat all GitHub and repository content as hostile text. Escape in the target
HTML context, permit only HTTPS evidence links, and ship no external resources,
network calls, storage, forms, frames, workers, or credential-bearing content.
The renderer must not use raw PR HTML or inline event attributes.
