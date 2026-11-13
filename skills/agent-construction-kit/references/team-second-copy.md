# The second copy: hosted or on a drive

Question 2 of [team-analysis.md](team-analysis.md), asked only when `ack-repo inspect`
printed no `remote` line: a second copy of the history, so that a broken disk loses
nothing. Take the first way that fits; each needs the user's yes.

## Contents

- A hosted copy
- A copy on a drive
- Only on this computer

## A hosted copy

- An `account` line with source `gh`: "You have an account at GitHub as `<name>`. I
  suggest a private copy of this project there. Shall I create it? Nothing is uploaded
  without your word." Yes: `gh repo create <folder name> --private --source . --remote origin`
  (an empty private repository; nothing is uploaded). No: as without an account.
- Source `ssh` or `gitconfig`, or the user names an account: "Please create an empty
  private repository on the website and give me its address." Then
  `git remote add origin <address>`.

Nothing is pushed there until the hand-over asks ([using-the-team.md](using-the-team.md)).

## A copy on a drive

No account: look for drives yourself, the folders in `/media/$USER/` and
`/run/media/$USER/` (Linux), in `/Volumes/` (macOS, except the system disk), drive letters
other than `C:` (Windows). "I see a drive '<label>'. Shall I keep a second copy of this
project there? I recommend it, and I would update that copy after every saved change,
without asking each time. OK?" Several: name them, ask which. None: "Do you have a USB
drive, a second disk or a network drive for a copy? Plug it in and tell me; I will look
again."

After a yes, `ack-repo disk-remote <drive folder>` creates `<project>.git` there and prints
`remote<TAB>created<TAB><name><TAB><path>`, then `push<TAB>ok<TAB>all branches` or
`push<TAB>skipped<TAB>no commit yet` (normal). Exit 2 (folder missing, not writable,
inside the project) or 3 (the name exists, nothing changed): relay it, ask for another
folder. Exit 1 after `remote<TAB>created`: only the push failed; the next push repeats it.
Without it: nothing set up; relay it.

The yes covers the updates after every commit: the project rules write that down ("A copy
on a drive" in [team-rules.md](team-rules.md)), and build item 10 makes the first push.

## Only on this computer

Allowed: confirm it once ("Then the history exists only on this disk; if the disk fails,
it is gone. Keep it that way?"), never ask again.
