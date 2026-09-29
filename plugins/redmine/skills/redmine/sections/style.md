# Style of Redmine comments

The reader is usually a manager or client deciding something. The comment must let them decide without
opening the code. Language: Russian unless the issue itself is in another language (then match it).

## Voice

- First person singular: «проверил», «предлагаю», «не смог воспроизвести». Not «мы», not impersonal passive
  where an actor is clear.
- No salutation, no addressing the reader by name, no sign-off. Start with the substance.
- Short and plain. One idea per sentence; cut anything the reader would not miss.
- No technical internals the manager does not need: class names, file paths, SQL, stack traces. Name a
  technical term only when the decision depends on it, with a phrase saying what it means for the product.
  Details go to a separate section or are offered on request.
- State what was actually checked and where (repository, stand, data), so the reader knows how solid it is.
  Mark guesses as guesses («предполагаю», «не проверял»).

## Structure

- Opening paragraph: the outcome in 1-3 sentences (what was found, what is proposed).
- `h2.`/`h3.` sections only when the comment has several distinct parts (findings, estimate, questions).
  A short reply needs no headings.
- **Questions to the manager: a numbered list** (`#`), each item starting with a bold short topic, then the
  question, self-contained (numbers must survive being quoted). Ask only what blocks the work; give your
  default when you have one («предполагаю, что ...»).
- **Options: A/B** (or A/B/C), each with its consequence (cost, risk, what stays unfixed). Say which one you
  recommend and why, in one line.
- **Estimates:** hours, as an upper bound plus buffer, broken down by part when there is more than one,
  with a total. Always mark it «примерная оценка» and say what could change it. State what is NOT included.
- MR link supplied by the user: a separate `h2.` section (for example «Merge request») with the link in Textile.
  Never invent or guess a link.

## Not in the comment

Internal reasoning, tool names, "I used subagents", drafts of alternatives you rejected, praise or apologies.
