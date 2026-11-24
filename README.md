![Agent Construction Kit](assets/github.png)

# agent-construction-kit

A Claude Code plugin that turns one long chat into a team of agents. You keep talking to
one session; it puts each job on a board and hands it to an agent made for that kind of
work, which starts with exactly the know-how it needs. One agent changes the code, another
checks it, and nothing is pushed or published without your word.

You do not write the team yourself, and you need not know how agents, skills or hooks
work. The kit reads your project, asks a few plain questions and writes the team into
your repository. It also sets up your machine, including Claude Code on other model
services and on local models.

You work with it through three commands; each asks one question at a time and does the work:

- `/agent-setup` **builds or checks the team**, from two starts. In your home folder it
  looks at what you work on and builds one admin folder that holds a card for this
  computer, with a team in each area you work in ([Start in your home folder](#start-in-your-home-folder)).
  In a project folder it reads your project, asks what it cannot read, shows a short
  plan, and after your yes writes the agents, their skills, their rules and their board
  into the repository and checks them.
  [The example below](#example-a-team-for-a-software-project) shows how that goes.
- `/agent-machine` **gets the machine ready.** It checks the plugins and tools agent teams
  build on, and creates starter commands such as `claude_with_kimi`: Claude Code running
  on another model provider, on a local model, or on OpenAI models through a ChatGPT
  subscription. At its end it offers `/agent-setup`.
- `/agent-tune` **reviews a team after real work** and proposes improvements; it only reads.

Claude never starts these three on its own: you type them. In full they are
`/agent-construction-kit:agent-setup`, `/agent-construction-kit:agent-machine` and
`/agent-construction-kit:agent-tune`; the short name works as long as no other plugin
uses it.

## Before you start

- [Claude Code](https://code.claude.com/docs/en/setup), installed and signed in.
- git. On Windows, [Git for Windows](https://git-scm.com/downloads/win): the kit's
  commands run in its bash. If git is missing, the setup helps you install it.

What the plugin the kit brings along still needs, and what is proven so far:
[Status](#status).

## Install

In Claude Code, type:

```
/plugin marketplace add Getty/marketplace
/plugin install agent-construction-kit@getty
/reload-plugins
```

One install brings both plugins an agent team builds on: this kit and skilletor, which
installs skills and rules into a project and keeps them current. The kit declares skilletor
as a dependency. `/reload-plugins` makes the new plugin available at once; restarting Claude Code does the
same. Then type `/agent-setup` in your home folder to set up the admin and the teams of
all your areas of work, or in a project folder to build that one team; `/agent-machine`
sets up the machine first.

## Start in your home folder

For someone who works on several things on one computer. One `/agent-setup` builds an admin
that steers your areas and holds a card for this computer, and a checked team in each area
you really work in.

1. Open a terminal and start Claude Code in your home folder: `cd`, then `claude`.
2. Type `/agent-setup`. It asks once: "May I look at the folder names in your home
   folder? I read names, whether files exist and the date of each repository's last
   commit, never what is inside a file." Your yes covers `ack-survey`, the command that
   looks, and it runs only after that yes; before it nothing of the home folder is read.
   On a no it asks only questions, and you name the folders.
3. Answer its questions, one at a time, each with its recommendation, in three blocks: the
   work environment (how far the admin reaches: only this computer, or also a home
   network or a lab); your work, paid or not, and the signs of it the look found, such as
   servers you run or Perl releases; and whether you work for customers.
4. It shows a plan with every folder on its own line and asks "Shall I build it?". Nothing
   is written until your yes.
5. It builds the areas first, each with its team, then the admin with `AREAS`, the list
   of the teams it steers, and its board, checks them, and saves one commit per folder.
6. Type `/exit`, then `cd admin` and `claude`: Claude Code loads agents only when a
   session starts.

Afterwards, for a user with the web shop `harbor`:

```
~/
  dev/harbor-shop/                  the shop, now with a team of its own
  admin/                            looks after this computer and steers the areas
    AREAS                           one row per area with a team: folder, kind, board
    BOARD.md                        the board: this computer first, then proposals
    CLAUDE.md
    .claude/                        the admin's rules, skill and read-only scout
```

Nothing is written into the home folder itself. The admin holds a card for this computer
on Linux, macOS and Windows alike; subagents that look after the computer are still to come
(see the [Roadmap](#roadmap)). If an admin already exists, no second one is built: start
Claude in its folder (`cd admin`, then `claude`) and type `/agent-setup` there. The admin
never edits, commits or pushes in an area: work for an area goes there as a card, and
you start Claude in that folder to have it done. What the look noticed and the kit does
not build yet becomes a card on the admin's board, so nothing is lost: from then on,
start Claude in `admin`, and type `/agent-setup` there to
add a team later.

## Your first team

1. Open a terminal and start Claude Code in your project folder:
   `cd "<your project>"`, then `claude`. An empty folder works too; the kit then asks
   what will be made in it.
2. Type `/agent-setup`. A sentence after it helps:
   `/agent-setup I have a small shop website here`.
3. Answer its questions. It reads first (how the project is built, tested and released,
   which conventions are written down, which repositories sit next to it) and asks only
   what it could not read: at most seven questions, each with its recommendation.
4. It shows a short plan and asks "Shall I build it?". Nothing is written into the
   project before that yes, except a git repository and a second copy of it, each with a
   yes of its own.
5. It builds the team, checks it, saves it as one commit and tells you how to use it.
6. Type `/exit` and start `claude` in the same folder again: Claude Code loads agents
   only when a session starts.
7. Give work in one sentence, as you would to a colleague.

Good to know:

- The setup makes decisions every later session works with, so run it on a strong model:
  Opus or Fable (`/model` switches). On a smaller one the kit stops and says why, and goes
  on only if you tell it to. In the finished team, each agent's model follows its work.
- Claude Code may ask you to allow each command the kit runs. That is its normal safety
  question.
- A folder that already has agents: `/agent-setup` checks that team, says what is missing
  and builds only that; it changes an agent file only with your yes.
- `/agent-setup` checks what a team needs and, with your yes, installs what is missing.
  `/agent-machine` is for the starters on other model services and local models, before
  or after.

## What an agent team is

One Claude Code session that does everything fills its memory with everything: your
conventions, the test output, the release steps, the half-read files. A team splits the
work the way people do.

- **Agents are cut from the work.** The kit looks at what the project delivers, how work
  is checked and who may do what, and draws task-derived boundaries: in a code project
  perhaps a scout that reads and reports, a worker that changes the code, a reviewer that
  checks independently and a committer that saves the work; other or fewer roles, as the
  work needs. Each agent is a small file in `.claude/agents/`.
- **Skills are the knowledge.** Your conventions live in skills, once. Each agent names
  the skills its role needs in the `skills:` list of its file, and Claude Code loads exactly
  those before the agent's first step. A narrow agent has room left to think, and can run a cheaper model.
- **Rules are the discipline.** The session you talk to does not touch the code itself;
  it hands work to the right agent. Nothing is pushed, published or sent without your
  word.
- **A board holds the work.** Every task is a card, so nothing exists only in a chat
  that scrolls away.

An extra agent earns its place only when its own context, tools, knowledge or permissions
improve the result: unnecessary hand-offs cost more than they save.

## Example: a team for a software project

You have a repository, say a web shop called `harbor`, and you type:
**`/agent-setup`**. After reading the project, it asks one question at a time:

> **Claude:** The history of `harbor` exists only on this computer. You have an account
> at GitHub as `sam`. I suggest a private copy of this project there. Shall I create it?
> Nothing is uploaded without your word.
>
> **You:** yes
>
> **Claude:** `harbor` is one web shop with its tests (`npm test`), so I suggest one team
> for this repository. Is that right?
>
> **You:** yes
>
> **Claude:** Your saved versions carry a name and an e-mail; both become visible if the
> project is ever published. Which shall I use?
>
> **You:** Sam Doe, sam@example.org
>
> **Claude:** Each job becomes a card on a board. The file `BOARD.md` needs nothing
> installed. karr is a board program that also passes cards between projects; I would
> download and install it for you. karr sends the cards, with the e-mail of whoever
> changed them, to your GitHub copy with every change. I recommend the file: karr pays
> off for a family of projects that hand work to each other.
>
> **You:** the file
>
> **Claude:** Here is my plan for `harbor`.
> - Five helpers: `harbor-scout` finds out where something is and changes nothing;
>   `harbor-worker` changes the code; `harbor-test-writer` writes the tests;
>   `harbor-reviewer` checks each finished job and runs `npm test`, and changes nothing;
>   `harbor-release-manager` saves reviewed work as commits. A checkout change needs a
>   test first and an independent check before it is saved; a smaller project gets
>   fewer helpers.
> - Their know-how: `harbor-core`, a skill written from your code and your `CONTRIBUTING.md`.
> - `OWNERS` says which helper changes which files.
> - The house rules: careful work, the helpers do the work, nothing leaves without your word.
> - The board: `BOARD.md`.
> - Saved work carries "Sam Doe <sam@example.org>", in this project only.
> - At the end I save all of this as one commit.
>
> Shall I build it?

After your yes, the repository has:

```
harbor/
  CLAUDE.md                         the team, one line per agent
  BOARD.md                          the board: to do, in progress, review, done
  OWNERS                            which agent changes which files
  .claude/
    agents/
      harbor-scout.md               reads and reports, changes nothing
      harbor-worker.md              implements, refactors, debugs
      harbor-test-writer.md         writes and extends tests
      harbor-reviewer.md            checks the diff and runs the tests, changes nothing
      harbor-release-manager.md     commits, changelog, moves the card to done
    rules/
      harbor-rules.md               what is true only for this project
      .local.*.md                   the house rules, kept current by skilletor
    skills/
      harbor-core/SKILL.md          architecture, vocabulary, invariants
    settings.json                   the plugins the team needs
    skilletor.json                  the skills and rules skilletor keeps current
```

Before it calls the team ready, the kit checks it: every agent file, every skill an agent
names (each must exist, since Claude Code skips an unknown name without a word), the
rules, the board and `CLAUDE.md`, and once, in a scratch folder, that a missing skill
shows up as a `skill` line.

From the next session on, work looks like this:

> **You:** The cart loses its coupon when the customer logs in.
>
> **Claude:** I made a card for it. `harbor-scout` is finding where the cart is merged
> on login.
> ... The coupon is dropped in `mergeCarts`. `harbor-test-writer` writes a failing test
> for it, `harbor-worker` fixes it.
> ... `harbor-reviewer` ran the suite: 212 tests pass, the new one included, and the
> change matches the card. `harbor-release-manager` committed it. Nothing is pushed;
> say the word when you want it out.

The session you talk to stays small: it holds the conversation and the cards, not the
code. Each agent starts fresh, with only the knowledge its role needs. Small things, like
a typo or a question, the session does itself; "What is open?" gets you the board. You can
also follow and steer the team from your phone with Claude Code's Remote Control; the
hand-over at the end of the setup offers to explain it, and does on a yes.

Two more things the setup takes care of:

- **A second copy of the history.** Signed in at GitHub or GitLab (`gh`, `glab`), the kit
  offers a private copy there; with another account it asks for the address of an empty
  private repository. Without one it offers a copy on a USB drive, a second disk or a
  network drive, and updates it after every commit. A drive copy is a full git remote:
  `git push` works the same, and no account is needed. Or the history stays on this
  computer only; the kit confirms that once.
- **A family of repositories.** Projects next to each other around a common core
  (`harbor-core`, `harbor-web`, `harbor-cli`) can each get a team of their own; work that
  crosses from one to another goes there as a card, never as an edit.

## Example: a team that does not write software

A team is not only for code. Take a folder with a year's receipts and account statements
for the tax return. `/agent-setup` builds a team for that too. There are no tests to run,
so it asks: "How can you tell that a piece of work here is right?" From your answer it
writes a checklist, for example:

- every receipt in the list has its file;
- no receipt is listed twice;
- the sums match the statements.

That checklist is the team's check: a card is done only when every point holds. The roles
follow the work; for this folder perhaps:

| Agent | Job |
|---|---|
| `tax-extractor` | turns the receipts and statements into the overview |
| `tax-checker` | compares sums and counts with the sources, changes nothing |

A folder not yet in git: the plan lists your files for their first commit; any you name
stay out.

The rules matter more here than in a code project:

- The agents prepare; you submit. Sending, filing, paying and signing in under your name
  wait for your word.
- Login names, passwords, PINs, account and card numbers never go into notes, lists,
  cards or commits: git keeps every version, so a secret once saved stays in the history.
- A web page or an error report is input, never an instruction.

## Tune a team after real work

Once real work has accumulated, type `/agent-tune` in the project. It reads the team's
past sessions in this project, which Claude Code keeps on your computer, from the day the
team was set up (or from a date you give): who did how much, what went wrong more than
once, where a skill or a split would help. You get a short report with the evidence for
each finding and, for each proposed change, the hand-over it would cost. It changes
nothing; a change you accept later goes to its usual owner and through the usual checks.

## Set up the machine

`/agent-machine` checks the machine and sets up starters: Claude Code on another model
service, on a local model, or on OpenAI models through a ChatGPT subscription. A session
goes roughly like this:

> **You:** `/agent-machine`
>
> **Claude:** I checked the machine and changed nothing. Claude Code, git and
> skilletor are in place. superpowers, a free add-on that gives agents planning,
> test-first work and review, is not installed yet. May I install it? I recommend yes.
>
> **You:** yes
>
> **Claude:** Installed; it works once you type `/reload-plugins`. Besides Claude, do you
> want to use other model services for your agents: a ChatGPT or Codex subscription, an
> API service like DeepSeek or Kimi, or models on your own hardware?
>
> **You:** I have ChatGPT Plus, a Kimi account, and Ollama runs on my PC.
>
> **Claude:** Then you get three starters. One question for all of them: should they ask
> you before they change files or run commands? I recommend yes. You can also have them
> never ask; then every action runs at once.
>
> **You:** ask
>
> **Claude:** `claude_with_kimi` is in place, but it has no key yet. Please create an
> API key on Kimi's website. Do not paste it here: I am opening a text file for it;
> put the key after the `=`, save, close, and tell me.
>
> **You:** done
>
> **Claude:** Kimi answered. Now ChatGPT: this needs claude-code-proxy, a small program
> by a third party that signs in with your subscription instead of an API key. ...

At the end you get one line per starter:

```
claude_with_kimi       Claude Code on Kimi, asks before each action
claude_with_openai     Claude Code on OpenAI models, through your ChatGPT subscription
claude_with_gemma      Claude Code on the Gemma model on this PC
```

What it can set up:

- The plugins agent teams build on: skilletor (required), superpowers and
  mattpocock-skills (recommended).
- One starter per provider you pick, for example `claude_with_kimi`. Type it in any
  terminal instead of `claude`; it takes the same arguments.
- If you want it, `claude_with_danger`: Claude Code as usual, with every permission
  question skipped.
- Starters for models on your own machine, or on a model server in your network that
  speaks the Anthropic Messages API.

Nothing is installed or changed without your yes. A few things are yours to do: you
paste each API key into a text editor that opens for it, you sign in to ChatGPT in your
browser if you want OpenAI models, and on Linux you may have to install git in a
terminal window, as that asks for your password.

## Providers

Ready-made definitions ship for these:

| Name | What it is | Key variable |
|---|---|---|
| `deepseek` | DeepSeek | `DEEPSEEK_API_KEY` |
| `fireworks` | Fireworks AI | `FIREWORKS_API_KEY` |
| `huggingface` | Hugging Face Inference Providers | `HF_TOKEN` |
| `kimi` | Moonshot AI Kimi | `MOONSHOT_API_KEY` |
| `minimax` | MiniMax (Anthropic-compatible API) | `MINIMAX_API_KEY` |
| `novita` | Novita AI | `NOVITA_API_KEY` |
| `ollama` | Ollama Cloud | `OLLAMA_CLOUD_API_KEY` |
| `openai` | OpenAI through claude-code-proxy (ChatGPT or Codex subscription) | none, you sign in with ChatGPT |
| `openrouter` | OpenRouter (one key, many vendors) | `OPENROUTER_API_KEY` |
| `qwen` | Alibaba Qwen (Coding Plan, international) | `DASHSCOPE_API_KEY` |
| `synthetic` | Synthetic (open models, flat subscription) | `SYNTHETIC_API_KEY` |
| `zai` | Z.ai GLM | `ZAI_API_KEY` |

`deepseek`, `novita`, `openrouter`, `qwen`, `synthetic` and `zai` are set up the way
their providers document it, but have not been tried with the kit yet (no account at
hand); the setup tells you so, and they may still need a change. Reports are welcome.

Each provider needs an account there and an API key, which is usually paid. `openai`
needs a ChatGPT Plus or Pro subscription instead. It goes through claude-code-proxy, a
program made neither by this kit nor by Anthropic or OpenAI; whether signing in that way
fits OpenAI's terms is your decision, and the setup says so before it installs anything.

Your keys stay in your environment or in a private key file that you fill in yourself,
in your own editor. The kit never writes a key and never shows one.

These are examples of one pattern, not the limit. Any service or model server with an
Anthropic-compatible API gets a starter the same way: tell the agent which one you use
(a company gateway, Vercel AI Gateway, LM Studio, llama.cpp, vLLM, ...), and it reads
that service's documentation and creates `claude_with_<name>` for it. Services that
only speak the OpenAI API (Groq, Cerebras, Mistral, Gemini, ...) need a translating
proxy such as LiteLLM or [Knarr](https://github.com/Getty/langertha-knarr) in front;
the agent tells you so.

## Reusing skills

Each team gets a project skill, `<prefix>-core` (`harbor-core` above), written from your
repository. Know-how you want in more than one project belongs in skills of its own:
skilletor installs them into each project and keeps them current. Before the kit writes a
skill, it uses what you already have: the skills installed here and the catalogs of the
sources you trust.

A preset is a skill the session lists whose description names this kit's commands and
that has a `## Answer sheet` section: `/agent-setup` and `/agent-machine` load it
themselves and ask only what it leaves open. Nothing is searched for or installed on the
kit's own initiative. With a preset, every team of a company, or of one person, starts
from the same answers: board, skill sources, roles, starters. The format is in
[team-answer-sheet.md](skills/agent-setup/references/team-answer-sheet.md).

You may keep your own collection of skills in a local folder, a private repository or a
hosted source; it holds `skills/<name>/SKILL.md`. Add it to a project and install from it
with `skilletor add mine "<local-directory-or-private-address>" --project` and
`skilletor install <name>@mine --project`. Edit a managed skill in its source, then run
`skilletor sync`; never hand-edit an installed copy. Choosing a collection does not create
a remote, publish or push it.

## Status

What is proven, and what is not yet:

- The kit is built for Linux, macOS and Windows alike. Its automated tests pass on all
  three (GitHub Actions); they run the scripts in a sandbox and check the skill text, not
  a live Claude Code session. Not yet confirmed: a fresh end-to-end run of the team build
  after the latest changes, the three commands started by typing them in a live session,
  and an interactive run of the machine setup and the team build on real macOS and
  Windows machines.
- The start in the home folder has had one real run: on Linux, in a sandbox home with
  sample folders, in a live Claude Code session, answered as a user with a web shop
  (`harbor`) and a home lab would. It built teams for the three `harbor` repositories
  (a family) and the admin, and the team check found nothing missing in them. The folder
  `ledger`, which already had a hand-made team, got only a `BOARD.md` (named in the
  plan); its own check still reports `settings` missing, which a card on the admin's
  board covers. Only today's kinds were built (software, a family, a folder without
  code); the lab and the blog posts became cards on the admin's board. Ways 2 and 3 of
  handing work over (a running session, a headless run) are not exercised. On macOS and
  Windows only the automated tests have run.
- Until its standalone binary is switched on, the plugin the kit brings along needs a
  runtime: skilletor needs Node.js 18 or newer. The kit's own commands are bash scripts and
  use neither Node.js nor Python; the team check reads agent files, skill folders and
  `settings.json` as text.
- Six of the twelve providers are set up from their documentation and not yet tried with
  the kit ([Providers](#providers)).

## Roadmap

1. **Machine setup**: prerequisites, starters for any model service, local models,
   OpenAI through a proxy. Done.
2. **The team itself**: reading the project, the questions, agents, rules, skills,
   board, and the check at the end, also for folders without code. Done; [Status](#status)
   says what is proven.
3. Sample projects that teach the team your conventions, per-language knowledge, and
   more roles for work without code: a collector that fetches documents with the
   browser.
4. The management hub: one admin that steers several teams from one folder, started from
   the home folder. Done for the admin and the kinds built today (software, a family, a
   folder without code). Still to come: the kinds `operations` (servers, a network or a
   lab), `machine` (the admin's subagents for this computer; until then the admin holds a
   card for it), `fleet` (packages released in a language), `content` (writing to
   publish), `pipeline` (material that comes in to be processed) and `customers` (one
   folder for each). Until then each is a card on the admin's board.
5. More boards: issue trackers.

## The commands

The commands above run these for you; you never need to type them. For the curious, they sit
in the plugin's `bin/` folder:

- `ack-doctor` checks the machine and changes none of your files; skilletor may fetch and cache
  its program. One line per item:

  ```
  plugin:skilletor   ok    skilletor is installed and enabled
  ```

- `ack-wrappers` creates, tests and removes the starters:

  ```
  ack-wrappers install kimi --permissions ask
  ```

- `ack-repo` reads a folder before a team is built (git, tests, sibling projects, an
  existing team) and changes nothing; `init` and `disk-remote` create the repository
  and a copy on a second drive:

  ```
  ack-repo inspect
  ```

- `ack-survey` reads the names in a folder, the home folder by default, and nothing
  inside any file; it is what the home start looks with, after your yes. One line per
  fact (the platform, projects with their last commit and team, signs of an area):

  ```
  project    /Users/sam/dev/harbor-shop    2026-11-18    none
  ```

- `ack-team` checks a finished team: every agent, every skill it names, the rules, the
  board, and that every skill an agent names exists:

  ```
  ack-team check
  ```

- `ack-proxy` looks after claude-code-proxy for the `openai` provider:

  ```
  ack-proxy status
  ```

## Platforms

Linux, macOS and Windows (with Git for Windows); [Status](#status) says what is proven on
each. The starters work from any shell; on Windows each one comes with a `.cmd` file.
That file hands its arguments to cmd.exe, which acts on `&`, `|`, `^` and `%` in them, so
from PowerShell or cmd put such an argument in quotes (`"a & b"`), or start the starter
from Git Bash, which passes arguments unchanged. Quotes do not protect `%NAME%`; for a
text with `%` use Git Bash.

## Remove everything

The commands sit in the plugin's `bin/` folder; Claude can run them for you.

1. `ack-wrappers list` shows your starters; `ack-wrappers uninstall <name>` removes one
   (on Windows with its `.cmd` file). A file the kit did not create stays.
2. On Linux, if you set up the proxy's background service: `ack-proxy service remove`.
3. Delete the kit's folders: `~/.local/share/agent-construction-kit` (the starters'
   copy of the kit), `~/.local/state/agent-construction-kit` (the proxy log) and
   `~/.config/agent-construction-kit` (your key files and your own providers; keep a
   copy of what you still need). `ACK_DATA_DIR`, `ACK_STATE_DIR` and `ACK_CONFIG_DIR`,
   or the `XDG_*_HOME` variables, move them elsewhere.
4. Delete the line ending in `# agent-construction-kit` from your shell startup file
   (`~/.bashrc`, `~/.zshrc`, `~/.bash_profile`, `~/.bash_login` or `~/.profile`), or the
   line you added yourself if the setup asked you to. On Windows, remove the
   starters' folder from your user `Path` in the environment variable settings.
5. In Claude Code: `/plugin uninstall agent-construction-kit@getty`.
   skilletor is a plugin of its own; if no team of yours uses it any more:
   `/plugin uninstall skilletor@getty`.

claude-code-proxy, if you installed it, is a program of its own: remove it the way you
installed it (with Homebrew: `brew uninstall claude-code-proxy`).

## License

Artistic-2.0, see [LICENSE](LICENSE).
