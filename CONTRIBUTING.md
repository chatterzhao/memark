# Contributing to MemArk

Thank you for your interest in contributing to MemArk!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/chatterzhao/memark.git
cd memark

# Create a virtual environment and install in development mode
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Git Workflow

MemArk follows a **Git Flow** model:

- `main` — stable releases only
- `develop` — integration branch for ongoing development
- `feature/*` — feature branches, branched from `develop`

### Branch Naming

- `feature/<short-description>` — new features
- `fix/<short-description>` — bug fixes
- `research/<topic>` — research and exploration

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add init --auto for one-step onboarding
fix: handle missing git directory in init
docs: update README with quickstart guide
ci: add GitHub Actions workflow
chore: update dependencies
```

### Pull Requests

1. Create a feature branch from `develop`
2. Make your changes with clear, atomic commits
3. Ensure all tests pass: `python3 -m unittest discover -s tests`
4. Open a PR against `develop`

## Worktree Governance

MemArk uses git worktrees to keep branches isolated. See `AGENTS.md` for the full worktree governance rules.

Key rules:
- The main worktree stays on `develop`
- Each feature branch gets its own worktree
- Dogfood and research branches have dedicated worktrees
- Do not develop directly on `develop`

## Running Tests

```bash
# Run all tests
python3 -m unittest discover -s tests -p 'test_*.py' -v

# Run a specific test
python3 -m unittest tests.test_cli.MemArkCliTests.test_init_adds_memark_to_gitignore
```

## Code Style

- Follow existing patterns in the codebase
- Use type hints where appropriate
- Keep functions focused and small
- Add docstrings to public functions

## Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Include reproduction steps and environment details

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
