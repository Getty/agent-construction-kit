# Using the team: the hand-over

What you tell the user when the team is built and checked, in plain words, and what
stays in `CLAUDE.md` for later (its section: [team-rules.md](team-rules.md)). Say it in
one message; offer Remote Control at the end, in a sentence, and explain it only on a yes.

## Contents

- The hand-over message
- Giving work
- Nothing leaves without your word
- Remote Control: the team on the phone
- With a hub (for a later version)

## The hand-over message

Example for `harbor`:

> The team for `harbor` is ready and checked.
> - Start Claude in this folder. The session you talk to hands the work to the right
>   agent.
> - Please close this session and start a new one first: the agents exist only for
>   sessions started after they were written.
> - Give work in one sentence, as you would to a colleague. Small things, like a typo or
>   a question, the session does itself; everything else becomes a card in `BOARD.md`,
>   goes to an agent, is checked by `harbor-reviewer` and saved as a commit.
> - Nothing is uploaded, released or posted without your word.
> - Everything I set up is saved as one commit here. It is not uploaded yet: shall I?

The start sentence is fixed: "Start Claude in this folder. The session you talk to hands
the work to the right agent." Name what `ack-team check` reported as `warn` in one
sentence each, and what you left out on purpose (a second copy declined, no tests yet).

## Giving work

- One sentence is enough: "The checkout page should show the total with tax." The
  session makes a card of it, hands it to the agent that owns that part, and comes back
  when the reviewer has checked it and the committer has saved it.
- "What is open?": the session reads the board and answers; the user can also open
  `BOARD.md` (with karr: `karr board`).
- The session does something itself that an agent should do: "Give that to the
  worker." The project rules say which work goes where.
- An agent does not start: a new session first; then `ack-team check` in the folder
  shows why.
- A card for something an issue tracker or an error report says: the user copies the
  part that matters into the request; the team never reads those systems on its own.

## Nothing leaves without your word

Commits stay on this computer. Pushing to a remote, releasing, deploying, and writing on
public trackers wait until the user says so, each time; a yes covers what it names
(house rule `publish-gate`). The one exception is what the project rules write down with
the user's yes, such as the push to a second copy on a disk.

## Remote Control

With Remote Control the user follows a running session from the phone or another
computer: read along, give tasks, answer questions. The kit does not switch it on; it
says how:

- In a running session type `/remote-control`, or start Claude with
  `claude --remote-control`.
- Then open the same session in the Claude app (iOS, Android) under "Code", or on
  claude.ai/code.
- For every session: `/config`, then "Enable Remote Control for all sessions".

It needs the same claude.ai account in both places, a subscription (it does not work
with an API key), and the computer stays on with Claude running. It works only with the
normal `claude`, not with a starter for another service (`claude_with_<name>`).

## With a hub

A structure that steers several teams (a hub) comes with a later version; until then,
never say these sentences. For that version they are ready, marked "with a hub":

- With a hub: "Start Claude always in `admin`; it steers the others."
- With a hub: "Start directly in `developer` only to talk with it alone; it then knows
  nothing about the agents around it; it can find out, but never guaranteed."
