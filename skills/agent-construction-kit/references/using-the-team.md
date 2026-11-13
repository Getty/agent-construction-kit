# Using the team: the hand-over

What you tell the user when the team is built and checked, in plain words, and what
stays in `CLAUDE.md` for later (its section: [team-rules.md](team-rules.md)). Say it in
one message; offer Remote Control at the end, in a sentence, and explain it only on a yes.

## Contents

- The hand-over message
- Giving work
- Nothing leaves without your word
- Remote Control: the team on the phone
- Next steps
- With a hub (for a later version)

## The hand-over message

Example for `harbor`, with a copy on the drive 'BACKUP':

> The team for `harbor` is ready and checked.
> - Start Claude in this folder. The session you talk to hands the work to the right
>   agent.
> - First type `/exit`, then start `claude` in this folder again: the agents exist only
>   for sessions started after they were written.
> - Give work in one sentence, as you would to a colleague. Small things, like a typo or
>   a question, the session does itself; everything else becomes a card in `BOARD.md`,
>   goes to an agent, is checked by `harbor-reviewer` and saved as a commit.
> - The first cards in `BOARD.md`: c1 "Tests for the checkout", c2 "Decide the shipping
>   costs", which needs your answer: which countries you ship to.
> - Nothing is uploaded, released or posted without your word. The one exception you
>   allowed: the copy on 'BACKUP' is updated after every saved change.
> - Everything I set up is saved as one commit, here and on 'BACKUP'.
> - You can also follow and steer the team from your phone (Remote Control). Shall I
>   tell you how?

The start sentence is fixed: "Start Claude in this folder. The session you talk to hands
the work to the right agent." Say it in the user's language, translated faithfully; in
`CLAUDE.md` it stays English, like the rest of that file. Name each first card
([team-board.md](team-board.md)) and, for one that needs the user's input, what it needs;
none: say the board is empty. Name what `ack-team check` reported as `warn` in one
sentence each, and what you left out on purpose (a second copy declined, no tests yet).
The last lines follow the second copy:

- A copy at GitHub or a similar service, file board: "It is not uploaded yet: shall I?"
  After a yes, `git push -u origin <branch>`.
- The same with karr, which sends only its cards: "The board's cards are already in that
  copy, as you allowed. Your files, the team's files and their history are not uploaded
  yet: shall I?"
- A copy on a drive: "Everything is saved here and on <drive>" (with karr the cards too).
- Only on this computer: "It is saved on this computer only."

## Giving work

- One sentence is enough: "The checkout page should show the total with tax." The
  session makes a card of it, hands it to the agent that owns that part, and comes back
  when the reviewer has checked it and the committer has saved it.
- "What is open?": the session reads the board and answers; the user can also open
  `BOARD.md` (with karr: `karr board`).
- The session does something itself that an agent should do: "Give that to the
  worker." The project rules say which work goes where.
- An agent does not start: type `/exit` and start `claude` again. Still not: the
  session runs the check ("Verification" in [team-rules.md](team-rules.md)) and says what
  is wrong.
- A card for something an issue tracker or an error report says: the user copies the
  part that matters into the request; the team never reads those systems on its own.

## Nothing leaves without your word

Commits stay on this computer. Pushing to a remote, releasing, deploying, and writing on
public trackers wait until the user says so, each time; a yes covers what it names
(house rule `publish-gate`). The exceptions are what the project rules write down
with the user's yes: the copy on a drive, updated after every commit, and with karr and a
remote `origin` the board, which karr sends there with every change.

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
normal `claude` (`claude_with_danger` is that too, with the permission questions
skipped), not with a starter for another service (`claude_with_<name>`).

## Next steps

After the hand-over, a sentence or two each, for what applies; nothing else:

- The analysis saw several repositories or areas: "The next version of the kit can
  steer several teams from one place (a hub); this team would become one of them."
- On Windows, always: "I recommend a second team later, in a folder of its own, only
  for this computer: updates, installed programs, the search path (PATH) and other
  settings, services, WSL, Git for Windows, and questions like 'why does X not work?'.
  A project agent should hand such work over instead of changing the system on the
  side. That team comes with the hub, in the next version of the kit."
- On Linux or macOS such a team for the computer only when the user asks about it.
- Only if the user asked for it, an issue tracker as the board: "That comes with a later
  version of the kit; until then you bring single entries in as cards."
- Only if the user asked about their machines or services (a homelab, an admin setup): "A
  later version of the kit can look, with your permission, at which computers and services
  you work with (your SSH settings, the hosts you know) and propose a structure for them."
- A preset named starters (`provider`): nothing of that was installed during the build.
  Name each one whose state `ack-wrappers list` shows as `absent` and offer to set it up
  ([machine.md](machine.md), step 2).

## With a hub

A structure that steers several teams (a hub) comes with a later version; until then,
never say these sentences. For that version they are ready, marked "with a hub":

- With a hub: "Start Claude always in `admin`; it steers the others."
- With a hub: "Start directly in `developer` only to talk with it alone; it then knows
  nothing about the agents around it; it can find out, but never guaranteed."
