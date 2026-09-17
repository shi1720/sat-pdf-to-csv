# SAT PDF to CSV

Extract text from SAT question PDFs and use a model-assisted parsing step to produce a reviewable CSV question bank.

**Stack:** Python / Streamlit. **Status:** reference implementation. Provider integrations require your own credentials and service access.

## Run locally

Use Python 3.12 and a virtual environment. Commands below run from the repository root.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock.txt
```

Where the interface asks for a provider key or backend address, supply your own authorized configuration at runtime. The repository does not supply access to an external service.

```bash
python -m streamlit run sat_question_processor.py --server.address 127.0.0.1
```

Open the localhost URL printed by Streamlit. Start with a small synthetic input, review the result, then export or continue the workflow.

## Repository map

| Path | Role |
| --- | --- |
| [`sat_question_processor.py`](sat_question_processor.py) | Application entrypoint and workflow logic |
| [`requirements.in`](requirements.in) | Direct Python dependencies |
| [`requirements.txt`](requirements.txt) | Compiled Python 3.12 dependencies with integrity hashes |
| [`requirements.lock.txt`](requirements.lock.txt) | Backward-compatible alias for the compiled requirements |
| [`.github/workflows/repository-quality.yml`](.github/workflows/repository-quality.yml) | Offline maintenance checks |

## Validation

```bash
python .github/scripts/repository_check.py --self-test
python .github/scripts/repository_check.py
```

CI checks Python syntax, local documentation links, credential patterns and locked dependency compatibility without importing the app or calling a model. Dependency validation contacts the package index; it does not install the application or use provider credentials. It does not establish grading accuracy or current provider availability. For integration validation, use synthetic examples and compare the output with known answers.

## Operating notes

Model names, remote endpoints and prompt assumptions reflect the original implementation. Review them before connecting current services. Keep provider keys, service-account files and private learning data outside the repository. Any credential previously committed must be rotated; removing it from the current tree does not invalidate earlier copies.

## Contributing

Keep changes focused and add regression coverage for behavior changes. Include synthetic reproduction data and the checks actually run. See the account [contribution guide](https://github.com/shi1720/.github/blob/main/CONTRIBUTING.md) and [private security reporting process](https://github.com/shi1720/.github/blob/main/SECURITY.md).

No open-source license is currently granted by this repository. Preserve existing ownership and obtain permission before reuse or redistribution.

## Refresh dependencies

```bash
uv pip compile --python-version 3.12 --universal --generate-hashes requirements.in --output-file requirements.txt
```

Validate the relevant provider integrations before deploying dependency updates. A lockfile fixes dependency resolution; it does not establish that a historical model endpoint is still available.

### Dependency update compatibility

`requirements.in` is the editable dependency manifest; `requirements.txt` is its compiled lockfile. This standard pip-compile layout lets Dependabot resolve parent and transitive dependencies together. Editing a transitive pin alone can produce an impossible environment (for example, Pydantic requires an exact pydantic-core version). Existing installs through `requirements.lock.txt` continue to use the same hashed lock.

Refresh with the command above. To request an upgrade, append `--upgrade-package PACKAGE`; retain the compatibility and application checks before merging.

### Anthropic model configuration

Claude Sonnet 3.5 and 3.7 have been retired by Anthropic. Requests now default to
`claude-sonnet-4-6`, the supported replacement. Set `ANTHROPIC_MODEL` to an
available Messages API model to override it; an empty value uses the default.
For the retrying generator, `ANTHROPIC_FALLBACK_MODEL` optionally selects a
separate fallback (otherwise retries keep the primary model). Restart the app
after changing configuration. Existing API-key settings remain unchanged.

Prompts, output schemas, token limits and sampling values are retained. The
SDK integrations send legacy sampling through `extra_body`, because Anthropic
Python 1.x removed the direct `temperature` keyword while Sonnet 4.6 still
supports it. If selecting a newer model, check its sampling compatibility.
Offline request regressions cannot establish equivalent grading quality: review
representative outputs before using a replacement model for real evaluations.
See [Anthropic model lifecycle](https://platform.claude.com/docs/en/about-claude/model-deprecations).

Run the isolated provider regressions with `python -m unittest discover -s tests -p 'test_claude*.py'`.
