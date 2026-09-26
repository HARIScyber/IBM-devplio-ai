# Three-minute demo script

## 0:00 — Problem

“Developers lose time figuring out unfamiliar repositories, finding risky code, and turning an issue into a safe, testable change. A generic chat window cannot show where its answers came from.”

## 0:20 — Solution

Open DevPilot AI and click **Try demo**. Point out the visible Demo Mode label. “DevPilot indexes a small example repository locally and gives each answer a file citation.”

## 0:40 — Repository overview

Show language/framework detection, files, entry points, repository tree, and the architecture summary. Explain that the sample repository is fictional and bundled for reliable judging.

## 1:00 — Repository chat

Ask: “How does account lookup work?” Show the cited `backend/auth.py` lines and the transparent retrieval-mode label. “With a configured provider, only retrieved excerpts are sent to the model; without one, this answer is local retrieval.”

## 1:25 — Security and bugs

Open Security and Code Analysis. Show severity, rule evidence, source line, and mitigation. Emphasize that findings are potential issues from static checks, not claims of exploitability.

## 1:50 — Planning and testing

Generate a plan for “Add OAuth authentication,” then generate a test draft for the auth module. Explain that generated output is a preview and never silently edits the repository.

## 2:20 — Docs and review

Show the generated documentation preview, then paste a small diff into PR Review to show summary and risk heuristics.

## 2:40 — IBM Bob development story

Show the real Bob IDE task history and `bob_sessions/` exports only after the team has created them. Describe the actual tasks performed: planning, implementation, debugging, or refactoring, with screenshots/session reports as evidence. Never claim unperformed Bob activity.

## 3:00 — Close

“DevPilot AI turns repository understanding into an end-to-end engineering workflow: understand, debug, test, secure, and ship—with evidence developers can verify.”


## Issue-to-verified-fix walkthrough

1. Load the bundled demo repository.
2. Open **Issue Workflow** and choose the sample email whitespace issue.
3. Run investigation and expand the cited `backend/auth.py` evidence.
4. Generate the plan, inspect the proposed unified diff, and generate the regression test.
5. Approve verification explicitly. Show that the same test fails before the proposed fix and passes after it in a temporary copy.
6. Run the final review and explain that the proposal is ready for human review; the project repository itself was not changed.
7. Open **Evaluation** and run the labeled retrieval benchmark. Describe its metrics as retrieval measurements, not answer-quality scores.
