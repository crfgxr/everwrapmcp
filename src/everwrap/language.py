"""Local language routing and selected NER models; no downloads during note access."""
import re
import os
from pathlib import Path

from .service import ProcessingBlocked
from .packs import PACKS, validate_languages

MODEL_ID = "akdeniz27/bert-base-turkish-cased-ner"
MODEL_REVISION = "99995f7d2be4b3a28c74f0d36ee97f8c04ee0571"
MODEL_FILES = ["config.json", "model.safetensors", "tokenizer.json",
               "tokenizer_config.json", "special_tokens_map.json", "vocab.txt"]
MODEL_PATH = ((Path(__file__).resolve().parents[2] / ".models") if os.name == "nt"
              else Path.home() / ".cache" / "everwrap") / MODEL_REVISION


def setup_model():
    """Explicit install step; only public model artifacts leave/enter this call."""
    from huggingface_hub import snapshot_download
    snapshot_download(MODEL_ID, revision=MODEL_REVISION,
                      allow_patterns=MODEL_FILES, local_dir=MODEL_PATH)


class LanguageAwareAnalyzer:
    def __init__(self, analyzer, english_nlp, languages=("en", "tr")):
        from lingua import LanguageDetectorBuilder
        import spacy
        self.enabled = validate_languages(languages)
        self.detector = LanguageDetectorBuilder.from_all_languages().build()
        self.english = english_nlp
        self.models = {"en": english_nlp} if "en" in self.enabled else {}
        import importlib
        for code in self.enabled:
            if code not in {"en", "tr"}:
                self.models[code] = importlib.import_module(PACKS[code]["model"]).load()
        self.tokens = spacy.blank("en")
        self.rules = analyzer
        # Regex/checksum detectors run for the entire text, regardless of routing.
        self.rules.registry.remove_recognizer("SpacyRecognizer")
        self.turkish = None
        if "tr" in self.enabled:
            from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
            import torch
            self.turkish = pipeline("token-classification",
                model=AutoModelForTokenClassification.from_pretrained(
                    str(MODEL_PATH), local_files_only=True, trust_remote_code=False,
                    use_safetensors=True),
                tokenizer=AutoTokenizer.from_pretrained(
                    str(MODEL_PATH), local_files_only=True, trust_remote_code=False),
                aggregation_strategy="simple", device=-1)
            # Keep CPU work bounded; models stay resident across reads.
            torch.set_num_threads(min(torch.get_num_threads(), 4))

    def languages(self, text):
        from lingua import Language
        scores = self.detector.compute_language_confidence_values(text)
        enabled = getattr(self, "enabled", ("en", "tr"))
        if not scores:
            return ()
        best = scores[0]
        code = {Language.ENGLISH: "en", Language.TURKISH: "tr",
                Language.SPANISH: "es", Language.FRENCH: "fr", Language.GERMAN: "de"}.get(best.language)
        if code not in enabled or best.value < .15:
            return ()
        return (code,)

    def turkish_entities(self, text):
        # Explicit token windows: do not rely on pipeline overflow behavior.
        offsets = self.turkish.tokenizer(text, add_special_tokens=False,
            return_offsets_mapping=True, truncation=False)["offset_mapping"]
        for index in range(0, len(offsets), 320):
            window = offsets[index:index + 400]
            start, end = window[0][0], window[-1][1]
            if not 0 <= start < end <= len(text):
                raise ProcessingBlocked("Invalid tokenizer offsets.")
            fragment = text[start:end]
            if len(self.turkish.tokenizer(fragment)["input_ids"]) > 512:
                raise ProcessingBlocked("Language window exceeds model bounds.")
            for entity in self.turkish(fragment):
                yield dict(entity, start=int(entity["start"]) + start,
                           end=int(entity["end"]) + start)
            if index + 400 >= len(offsets):
                break

    def analyze(self, *, text, language="en", score_threshold=.35):
        from presidio_analyzer import RecognizerResult
        from presidio_analyzer.nlp_engine import NlpArtifacts
        try:
            doc = self.tokens(text)
            artifacts = NlpArtifacts(entities=[], tokens=doc,
                tokens_indices=[t.idx for t in doc], lemmas=[t.text.lower() for t in doc],
                nlp_engine=None, language="en")
            matches = self.rules.analyze(text=text, language="en",
                score_threshold=score_threshold, nlp_artifacts=artifacts)
            # Sentence/paragraph units handle language switches within a note.
            # Keep exact source offsets; no normalization or reconstruction here.
            segmentation = re.sub(r"[^\s@]+@[^\s@]+", lambda m: m.group().rstrip(".!?").replace(".", "_") + m.group()[len(m.group().rstrip(".!?")):], text)
            # German written dates use a dot after the day, not a sentence boundary.
            segmentation = re.sub(r"(?<=\d)\.(?=[ \t]+(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\b)", "_", segmentation, flags=re.IGNORECASE)
            for unit in re.finditer(r"[^\n.!?]+(?:[.!?]+|$)|[^\n]+$", segmentation, re.MULTILINE):
                part = text[unit.start():unit.end()]
                if (not any(c.isalpha() for c in part)
                        or part.strip() in {"[SECRET]"}):
                    continue
                langs = self.languages(part)
                if not langs:
                    matches.append(RecognizerResult("LANGUAGE_UNSUPPORTED", unit.start(), unit.end(), 1.0))
                    continue
                for code in (code for code in langs if code in self.models):
                    mapping = {"PERSON": "PERSON", "PER": "PERSON", "MISC": "NRP", "ORG": "ORGANIZATION",
                               "GPE": "LOCATION", "LOC": "LOCATION", "FAC": "LOCATION",
                               "DATE": "DATE_TIME", "TIME": "DATE_TIME", "NORP": "NRP"}
                    for entity in self.models[code](part).ents:
                        if entity.label_ in mapping:
                            matches.append(RecognizerResult(mapping[entity.label_],
                                unit.start() + entity.start_char, unit.start() + entity.end_char, .85))
                if "tr" in langs:
                    # Overlapping token windows cover every part, including long tails.
                    for entity in self.turkish_entities(part):
                        kind = {"PER": "PERSON", "ORG": "ORGANIZATION", "LOC": "LOCATION"}.get(entity["entity_group"])
                        start, end = int(entity["start"]), int(entity["end"])
                        if not kind or not 0 <= start < end <= len(part):
                            raise ProcessingBlocked("Invalid language detector output.")
                        matches.append(RecognizerResult(kind, unit.start()+start,
                                                       unit.start()+end, float(entity["score"])))
            return matches
        except Exception:
            # Exceptions from tokenizers/models can include source text.
            raise ProcessingBlocked("Local language analysis failed.") from None


if __name__ == "__main__":
    setup_model()
    print("Pinned Turkish model installed for local inference.")
