# Repository Guidelines

## Project Structure & Module Organization
This repository is documentation-first. Core project intent is in `README.md`.

- `Templates/`: canonical D1-D10 specification templates and process standards (for example `D1_CONSTITUTION.md`, `D8_TASKS.md`, `BUILDER_HANDOFF_STANDARD.md`).
- `architecture/`: system-level authority docs and analysis artifacts (for example `NORTH_STAR.md`, `BUILDER_SPEC.md`, `OPERATIONAL_SPEC.md`, `SAWMILL_FLOW.pdf`).
- Root files: repository metadata (`LICENSE`, `.gitignore`) and contributor guidance.

Keep new content in the closest existing domain folder; avoid creating new top-level directories unless the structure no longer fits.

## Build, Test, and Development Commands
There is no compile/build pipeline in this repo. Validate changes through document quality checks.

- `rg --files`: quick inventory of tracked files.
- `rg "^#|^##" Templates architecture`: verify heading structure and section consistency.
- `git diff -- Templates architecture`: review only docs you changed before committing.
- Optional lint (if available): `npx markdownlint-cli2 "**/*.md"`.

## Coding Style & Naming Conventions
Use clear, instructional Markdown with short sections and explicit headings.

- Headings: sentence case or title case, but be consistent within a file.
- Lists: prefer concise bullets over long paragraphs.
- Filenames: use uppercase, underscore-separated patterns for templates (for example `D4_CONTRACTS.md`) and descriptive uppercase names for architecture authorities (for example `OPERATIONAL_SPEC.md`).
- Keep YAML keys stable in `Templates/AGENT_BUILD_PROCESS.yaml`; preserve existing schema names when editing.

## Testing Guidelines
Testing is documentation validation.

- Confirm internal references, filenames, and command snippets are accurate.
- For process changes, verify cross-document consistency between `Templates/GUIDE.md`, template files, and architecture authorities.
- Treat broken links, stale paths, and contradictory rules as test failures.

## Commit & Pull Request Guidelines
Git history currently starts with a single bootstrap commit (`Initial commit`), so no strict historical convention exists yet.

- Commits: use imperative, scoped messages (for example `docs(templates): clarify D6 gate criteria`).
- PRs should include: purpose, files changed, rationale, and any downstream docs requiring follow-up.
- For architecture-impacting changes, cite the authority chain (`NORTH_STAR.md` -> `BUILDER_SPEC.md` -> `OPERATIONAL_SPEC.md`) and explain consistency.
