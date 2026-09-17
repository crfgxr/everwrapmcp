# Presidio redaction

Set `content_mode` to `redacted` in the private local policy to mask detected
sensitive text from permitted notes. The block list remains authoritative:
redaction never makes a blocked note readable. No tool argument can disable
masking, modify access, or request a raw fallback.

Date/time masking defaults to on. Set `"mask_dates": false` in the private local
policy to preserve spans detected as `DATE_TIME`, including date headings, times,
and birthday dates. Other detected entity types and the block list remain enforced;
overlapping secret or other sensitive matches still win. This setting cannot be
changed through tool arguments. Search timestamp metadata is still omitted in
redacted mode. Restart an older server after updating to load this policy option.

## Data flow

1. Load and validate local policy. Deny blocked direct IDs before network access.
2. Initialize the installed local Presidio/NLP runtime. Missing models fail closed;
   the server does not download models or call remote inference during requests.
3. Fetch the permitted note, or discard blocked upstream search rows locally.
4. Flatten ENML/HTML bodies and snippets with an inert parser. Drop attributes,
   comments, scripts/styles, encrypted payloads, and attachment references.
5. For note reads, select a bounded section locally (optionally by a recognized
   date heading or keywords), retaining neighboring sections for detection context.
   See [large-note selection and pagination](LARGE_NOTES.md).
   Normalize character entities, Unicode compatibility forms, and invisible format
   characters. Run shared Presidio patterns/checksum recognizers across the complete
   window. Route sentence/paragraph units with Lingua to selected English/Spanish/French/German spaCy or Turkish
   BERT NER according to the selected local packs. Unsupported or uncertain units
   are withheld as `[LANGUAGE_UNSUPPORTED]` (overlaps may become `[REDACTED]`). Turkish inference uses overlapping 400-token
   windows with an 80-token overlap, so long tails are not silently truncated.
6. Merge overlapping detected spans and use Presidio Anonymizer to replace them
   with typed placeholders. Page only after masking; return only processed text
   and explicit section/continuation metadata.
7. Omit search timestamps in redacted mode. Retain routing UUIDs for follow-up
   reads. Recheck that policy did not change before returning output.

Example using synthetic text:

```text
Before: Talk to Alex Smith about the chatbot.
After:  Talk to [PERSON] about the chatbot.
```

Other placeholders include `[EMAIL_ADDRESS]`, `[PHONE_NUMBER]`, `[DATE_TIME]`,
`[LOCATION]`, `[SECRET]`, and `[REDACTED]`. Overlapping entity types can produce a
generic placeholder. Returned note bodies use `content_format: "plain_text"` and
`content_mode: "redacted"`. Formatting is reduced, and link targets are omitted.

Any invalid input, detector error, missing model, failed anonymization, malformed
result, or changed policy blocks the entire tool response. There is no raw fallback.
The server suppresses library logging and returns static errors, not exception
text or detected values. Intermediate raw data stays in the wrapper's memory.

## Coverage and limits

This is automatic **best-effort masking**, without a human approval step. It uses
Selected statistical NER for five languages with multilingual label patterns. Lingua
checks its full language set, but only selected supported packs can produce
readable output. Purely numeric units still use shared rules and the date preference.
The language-confidence cutoff is a heuristic, not a calibrated privacy guarantee.
Mixed-language sentences and short ambiguous text can still be misclassified. Contextual names, unusual addresses, ambiguous birthdays, unfamiliar
credentials, and encoded/obfuscated forms may be missed. Recognizers also produce
false positives; conservative label patterns can mask more than the sensitive span.
Removing detected PII does not remove instructions embedded in note text.

See [the synthetic report](redaction-results.json) for current fixture results.
Passing fixtures does not guarantee complete privacy. The separate historical
stock-baseline report and its six failing tests remain unchanged.

The generic capitalized-words-as-person pattern was removed because it masked
ordinary headings. Explicit name labels remain. No global confidence increase or
removal of PERSON/ORGANIZATION protection was used to improve readability.

The Turkish model is `akdeniz27/bert-base-turkish-cased-ner`, revision
`99995f7d2be4b3a28c74f0d36ee97f8c04ee0571` (MIT). Install it explicitly with
the [language-pack installer](INSTALL.md#choose-language-packs). Runtime loads only local
safetensors weights, forbids remote code, and makes no inference network requests.
Model artifacts live outside the repository under `~/.cache/everwrap/`.
Selected models stay resident; first initialization is slower than warm
requests. There are no additional LLM tokens for this local masking step.
See [dependency review](DEPENDENCY_SECURITY.md) for the dated audit and its limits.

Run actual engine tests and the synthetic benchmark with:

```sh
.venv/bin/python -m pytest tests/test_redaction.py -q
PYTHONPATH=src .venv/bin/python -m experiments.redaction
```

The report contains synthetic examples only. Do not add real note content,
identifiers, account links, or the private block list to reports or fixtures.

Presidio reference: https://presidio.dataprivacystack.org/anonymizer/

## Language-routing validation (2026-09-17)

The application regression suite passed 260 tests (historical stock baseline
excluded), including missing-model/error-sanitization checks. The targeted
language suite passed all 14 tests. Tests include ordinary
Turkish prose, bilingual names, contacts, secrets, addresses, long-token-window
tails, block-before-fetch, and absence of raw fallback. The synthetic corpus now
passes 25/26; the remaining false positive masks the programming name `asyncio`.
Both exploratory name cases pass, without establishing general recall.

Ten warm local runs of a short, synthetic Turkish two-sentence passage averaged
about 50 ms on the development Mac. This excludes model startup, Evernote network
time and large-note processing; it is not an end-to-end latency promise. Real-note
search should be repeated after the MCP process is restarted to load the change.

## Historical two-language pack validation

The language-pack update passed 274 current regression tests (excluding the
separate historical stock-baseline gate). A final 16-test pack suite also passed,
including two added checks for a policy change during a read and a missing model
blocking access before any upstream fetch. Coverage includes selected-pack loading,
English/Turkish fictional names, unsupported French/Spanish passages, numeric dates,
atomic policy updates preserving exclusions, and setup failure leaving policy intact.
The installation subprocess is mocked in setup tests; a fresh-machine installation
and live-note verification are still separate checks. No personal notes are fixtures.
