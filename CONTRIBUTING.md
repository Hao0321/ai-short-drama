# Contributing

Contributions are welcome, especially for original genre engines, format routing, platform-aware validation patterns, production-pack tooling and reproducible quality checks.

Before opening a pull request:

1. Keep concrete story characters, scenes and dialogue original or properly licensed.
2. Do not commit private series Bibles, likeness／voice assets, credentials, cookies or generated media with unclear rights.
3. Keep `SKILL.md` focused on routing and hard rules; put detailed knowledge in `references/`.
4. Run `python -m py_compile scripts/drama_lint.py scripts/studio_lint.py`, `python -m unittest discover -s tests -v`, and validate all changed JSON files.
5. Add or update an eval case when changing a core behavior.
6. Date and cite volatile model capabilities, platform policies and rankings; do not encode them as permanent facts.
