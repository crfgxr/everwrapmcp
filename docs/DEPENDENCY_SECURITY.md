# Dependency review — 2026-09-17

EverWrapMCP is Python, not npm. No npm package was added. We checked the actual
Python dependency graph with pip-audit 2.10.1 against its default PyPI advisory
service. [Machine-readable installed-environment report](dependency-audit.json).

- The proposed NLP dependency resolution contained 35 packages and reported no
  known vulnerabilities.
- The installed environment initially reported six advisory entries in
  cryptography 48.0.1, representing three distinct PYSEC IDs (3552, 3553, 3554
  in 2026). Upgraded to 50.0.1 and pinned that version in requirements-live.txt.
- The final installed macOS environment scan covered 90 packages with no known
  vulnerabilities reported. The direct-URL English spaCy model wheel was skipped
  by pip-audit; it remains pinned to the publisher's 3.8.0 release in uv.lock.
- This is an advisory scan, not proof of safety or a model-quality review. It does
  not cover every platform-specific dependency in the universal lock or the NLP
  weights. Re-run it as dependencies/advisories change.

FastText was considered, but its original upstream repository is archived. We
selected Lingua 2.2.0 for local EN/TR language identification instead. Its models
ship with the package; installation is larger than fastText's compressed model.
Transformers 5.17.0, torch 2.14.0 and safetensors 0.8.0 are pinned. The Turkish
model is pinned to an immutable revision, downloaded explicitly during setup,
and loaded with local_files_only=True, trust_remote_code=False and
use_safetensors=True. Runtime note handling never downloads a missing model.

Sources:
- [FastText upstream archive](https://github.com/facebookresearch/fastText)
- [Lingua upstream](https://github.com/pemistahl/lingua-py)
- [Turkish NER model and license](https://huggingface.co/akdeniz27/bert-base-turkish-cased-ner)
- [pip-audit](https://github.com/pypa/pip-audit)

Audit reproduction (put the audit tool in a separate environment):

```sh
uv pip freeze --python .venv/bin/python > /tmp/everwrap-installed.txt
pip-audit -r /tmp/everwrap-installed.txt --no-deps --disable-pip
```

`--no-deps` here audits an already complete installed dependency list, rather than
asking pip-audit to install or resolve the application again. Model weights and
private policies are not included in reports or sent to the advisory service.

## Five-language pack update

A rescan with pip-audit 2.10.1 found no known vulnerabilities in **90 assessed
packages**. Four direct-URL wheels were skipped: English en_core_web_lg and Spanish,
French and German core_news_md. Those wheels and their weights were **not assessed**;
this is not evidence that they are vulnerability-free. All are pinned official
spaCy 3.8.0 releases. The new models add no package dependencies to the installed
environment. See [the new report](dependency-audit-five-languages.json) and
[model licenses](LANGUAGE_PACKS.md#models-and-licenses).

The advisory result applies to the installed environment **after**
`requirements-live.txt`, which pins patched cryptography. The universal core lock
still resolves the older version; plain `uv sync` can restore it. Always reinstall
the live requirements after syncing, as the installation guide requires. Aligning
the universal lock with the patched platform packages remains a packaging gap.
