# Presidio redaction

Set `content_mode` to `redacted` in the private local policy to mask detected
sensitive text from permitted notes. The block list remains authoritative:
redaction never makes a blocked note readable. No tool argument can disable
masking, modify access, or request a raw fallback.

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
   characters. Run Presidio Analyzer with the installed English NLP model and
   supplemental English/Turkish patterns plus credential recognizers.
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
English statistical NER with extra bilingual patterns, **not a trained Turkish
NER model**. Contextual names, unusual addresses, ambiguous birthdays, unfamiliar
credentials, and encoded/obfuscated forms may be missed. Recognizers also produce
false positives; conservative label patterns can mask more than the sensitive span.
Removing detected PII does not remove instructions embedded in note text.

The regression corpus passes 24/26 checks, including removal of all targeted
sensitive values. The two failures are utility false positives (`asyncio` and a
harmless Turkish word). Passing fixtures does not guarantee complete privacy.
The separate stock-baseline report and its six failing tests remain unchanged.

Run actual engine tests and the synthetic benchmark with:

```sh
.venv/bin/python -m pytest tests/test_redaction.py -q
PYTHONPATH=src .venv/bin/python -m experiments.redaction
```

The report contains synthetic examples only. Do not add real note content,
identifiers, account links, or the private block list to reports or fixtures.

Presidio reference: https://presidio.dataprivacystack.org/anonymizer/
