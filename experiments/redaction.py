"""Synthetic regression and challenge report for the actual local redactor."""

import json
from pathlib import Path

from experiments.baseline import CASES as BASELINE_CASES
from everwrap.redaction import get_redactor


CASES = [*BASELINE_CASES,
    ("english_context_name", "My name is Mira Patel. Build the chatbot.", ["Mira", "Patel"]),
    ("turkish_context_name", "adım deniz aksoy. chatbot hazır.", ["deniz", "aksoy"]),
    ("unicode_full_name", "Selin Öztürk ile görüşme yapıldı.", ["Selin", "Öztürk"]),
    ("english_birthday", "Birthday: September 6, 1987\nBuild the chatbot.", ["September", "1987"]),
    ("turkish_birthday_new", "Doğum tarihim: 23 Eylül 1988\nchatbot hazır.", ["Eylül", "1988"]),
    ("numeric_date", "Appointment 2026-10-09. Build the chatbot.", ["2026-10-09"]),
    ("english_address", "Address: 482 Willow Avenue, Bristol\nBuild the chatbot.", ["482", "Willow", "Bristol"]),
    ("turkish_address", "Adres: Bahar Mahallesi Çiçek Sokak No: 18 Ankara\nchatbot hazır.", ["Bahar", "Çiçek", "18", "Ankara"]),
    ("turkish_password", "şifre: kurmaca-parola-927\nchatbot hazır.", ["kurmaca-parola-927"]),
    ("quoted_secret", 'password="synthetic phrase with spaces"\nBuild the chatbot.', ["synthetic phrase with spaces"]),
    ("zero_width_secret", "password=syn\u200bthetic-hidden-927", ["synthetic-hidden-927", "syn\u200bthetic-hidden-927"]),
    ("html_entity_email", "Write to mira&#64;example.org about the chatbot.", ["mira@example.org", "mira&#64;example.org"]),
    ("private_key", "-----BEGIN PRIVATE KEY-----\nsynthetic-private-material\n-----END PRIVATE KEY-----", ["synthetic-private-material"]),
    ("basic_auth", "Authorization: Basic c3ludGhldGljOnBhc3N3b3Jk", ["c3ludGhldGljOnBhc3N3b3Jk"]),
    ("turkish_utility", "chatbot için olay tabanlı mimari kullan.", []),
    ("code_utility", "Use asyncio to process messages and retry failed requests.", []),
]

# Report these without converting exploratory results into a coverage guarantee.
# They exercise gaps beyond the targeted fixtures above.
CHALLENGES = [
    ("lowercase_turkish_name", "bugün zeynep demir ile konuştum.", ["zeynep", "demir"]),
    ("contextual_single_name", "the person in the blue coat was mira.", ["mira"]),
]


def evaluate(redactor, cases):
    rows = []
    for label, source, forbidden in cases:
        output = redactor.sanitize_text(source)
        passed = (all(value.casefold() not in output.casefold() for value in forbidden)
                  if forbidden else output == source)
        rows.append({"case": label, "passed": passed, "output": output})
    return rows


def run():
    redactor = get_redactor()
    rows = evaluate(redactor, CASES)
    challenges = evaluate(redactor, CHALLENGES)
    report = {
        "configuration": "Local Presidio + en_core_web_lg + bilingual patterns and credential recognizers",
        "synthetic_only": True, "guarantees_complete_detection": False,
        "passed": sum(r["passed"] for r in rows), "total": len(rows),
        "results": rows, "exploratory_challenges": challenges,
        "turkish_statistical_ner": False,
    }
    Path("docs/redaction-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
