# Changelog

## 1.0.6

- Support omp and other MCP-capable harnesses alongside Claude Code: discover actual tool schemas and invocation interfaces, resolve bundled paths from SKILL.md, and use the available structured-choice tool for intake.

## 1.0.5

- Instance address comes from VIKUNJA_URL instead of a hardcoded host; task language and relation wording follow the project; examples made generic.

## 1.0.4

- Intake offers the brainstorm with AskUserQuestion buttons instead of a text question.

## 1.0.3

- Intake: brainstorm by default, a plan only when the task already spells out the solution.

## 1.0.2

- Backlog: when no project matches, list all projects and ask. Title prefix yields to the neighbours' scheme; search by Russian word stems.

## 1.0.1

- Relations: document verified semantics (kind = what otherTaskId is to taskId) and that the MCP reply text for subtask/parenttask is inverted; drop the "recreate if reply looks reversed" rule. Note that task_delete only marks tasks done.

## 1.0.0

- Vikunja skill with backlog, intake and report scenarios, conventions reference and an HTML validator.
- Commands /vikunja:backlog, /vikunja:intake, /vikunja:report.
- Eval cases for the three scenarios.
