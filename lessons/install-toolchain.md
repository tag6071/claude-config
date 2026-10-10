---
triggers:
  - '\b(pipx|brew|npm|pnpm|yarn|pip|pip3|gem|cargo|go|apt|poetry|uv)\s+(install|add)\b'
  - '\binstall (a|the|this|that)?\s*(package|dependency|dep|library|module|tool)\b'
  - '\badd (a|the|this|that)?\s*(dependency|dep|package|library)\b'
---
[rule:install-toolchain] Before suggesting ANY install command, check the project's toolchain manifest FIRST (pyproject.toml, package.json, requirements.txt, Cargo.toml, Gemfile, go.mod) and use ITS conventions. uv repo -> add to pyproject + `uv sync`, never pipx. npm/yarn/pnpm repo -> local install, never `-g`. Adding a dep outside the lockfile breaks fresh-clone reproducibility.
