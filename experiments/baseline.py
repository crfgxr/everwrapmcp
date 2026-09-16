"""Measure the stock English NLP configuration, including Turkish challenge cases.

No real notes, credentials, network inference, or production sanitizer.
"""
import json
from pathlib import Path
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

CASES = [
    ("english_person", "Talk to Alex Smith about the chatbot.", ["Alex", "Smith"]),
    ("email", "Contact alex@example.com about the chatbot.", ["alex@example.com"]),
    ("turkish_phone", "Telefon: +90 555 123 45 67", ["555"]),
    ("turkish_person", "Yarın Ayşe Yılmaz ile chatbot projesini konuşacağım.", ["Ayşe", "Yılmaz"]),
    ("turkish_birthday", "Doğum günüm 14 Mart 1992.", ["14 Mart", "1992"]),
    ("openai_key", "OPENAI_API_KEY=sk-test-secret-value", ["sk-test-secret-value"]),
    ("password", "password=synthetic-password-742", ["synthetic-password-742"]),
    ("bearer", "Authorization: Bearer synthetic-token-742", ["synthetic-token-742"]),
    ("connection_string", "postgresql://demo:synthetic-pass@localhost/demo", ["synthetic-pass"]),
    ("useful_text", "The chatbot architecture should use an event-driven approach.", []),
]

def run():
    provider = NlpEngineProvider(nlp_configuration={"nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}]})
    analyzer = AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["en"])
    anonymizer = AnonymizerEngine()
    rows = []
    for label, source, forbidden in CASES:
        results = analyzer.analyze(text=source, language="en")
        output = anonymizer.anonymize(text=source, analyzer_results=results).text
        leaked = any(value.casefold() in output.casefold() for value in forbidden)
        rows.append({"case": label, "passed": not leaked if forbidden else output == source,
                     "entities": sorted({r.entity_type for r in results}), "output": output})
    report = {"configuration": "Presidio defaults + en_core_web_lg; Turkish evaluated as challenge input, not claimed supported",
              "synthetic_only": True, "passed": sum(r["passed"] for r in rows), "total": len(rows),
              "production_ready": False, "results": rows}
    Path("docs/baseline-results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    run()
