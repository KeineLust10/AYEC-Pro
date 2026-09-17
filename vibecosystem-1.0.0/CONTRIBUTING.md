# Contributing to vibecosystem

Thanks for considering contributing! Here's how you can help.

## Ways to Contribute

### Add New Agents
Create a new `.md` file in `agents/` following the existing format (YAML frontmatter + prompt body). Focus on domain-specific roles not yet covered.

### Add New Skills
Add reusable knowledge patterns to `skills/`. Each skill should be a `prompt.md` or `SKILL.md` with clear trigger conditions and instructions.

### Improve Hooks
TypeScript hooks live in `hooks/src/`. New sensors, smarter context injection, better intent classification — all welcome.

### Documentation & Translations
Improve existing docs, add tutorials, or translate README to new languages. Existing translations are in `docs/`.

### Bug Reports & Feature Requests
Open an issue with a clear description. Include your Claude Code version and OS.

## Development Setup

```bash
git clone https://github.com/vibeeval/vibecosystem.git
cd vibecosystem
./install.sh
```

## Pull Request Process

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-new-agent`)
3. Commit with clear messages
4. Push and open a PR against `main`
5. Describe what you added and why

## Code Style

- Agents: Markdown + YAML frontmatter
- Hooks: TypeScript, built with esbuild
- Skills: Markdown (prompt.md or SKILL.md)
- Rules: Markdown

## Good First Issues

Look for issues labeled `good first issue` — these are beginner-friendly tasks.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
