## Summary (written by you)

<!-- Required: at least one sentence in your own words, not AI-generated: what this changes and
why. Any language is fine. PRs without it are closed (see CONTRIBUTING.md). -->

## Details

<!-- Optional. AI-assisted text is fine here. -->

## Checklist

- [ ] `uv run python -I tools/build.py` succeeds
- [ ] `uvx ruff check --select E,F,W --line-length 120 tools/` passes
- [ ] firmware output unchanged ("matches the released build"), **or** changed on purpose and
      `EXPECTED_SHA256`, the README hashes and `docs/before-after.png` are updated
- [ ] user-facing changes are in all READMEs (or noted here for translators)
- [ ] tested by: build only / flashed to a real iPod (model: )
