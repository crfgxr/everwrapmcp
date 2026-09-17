"""Interactive local language-pack setup. Never reads Evernote notes."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from .policy import SingleNotePolicy

PACKS = {
    "en": {"name": "English", "packages": ["https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl"],
           "sample": "Talk to Alex Smith about the community garden.", "private": ["Alex", "Smith"]},
    "tr": {"name": "Turkish", "packages": ["transformers==5.17.0", "torch==2.14.0", "safetensors==0.8.0"],
           "sample": "Bugün Ayşe Yılmaz ile konuştum.", "private": ["Ayşe", "Yılmaz"]},
}


def validate_languages(values):
    if not values or any(x not in PACKS for x in values) or len(set(values)) != len(values):
        raise ValueError("Select English (en), Turkish (tr), or both; other packs are not available.")
    return tuple(sorted(values))


def save_languages(path, languages, original):
    """Replace only the language selection; preserve exclusions and access modes."""
    languages = validate_languages(languages)
    if path.read_bytes() != original:
        raise ValueError("Local policy changed during setup; rerun setup.")
    SingleNotePolicy.from_file(path)
    data = json.loads(original)
    data["languages"] = list(languages)
    payload = (json.dumps(data, indent=2) + "\n").encode()
    if len(payload) > 1024:
        payload = json.dumps(data, separators=(",", ":")).encode()
    if len(payload) > 1024:
        raise ValueError("Updated policy exceeds supported size.")
    fd, name = tempfile.mkstemp(prefix=".everwrap-policy-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
        SingleNotePolicy.from_file(Path(name))
        if path.read_bytes() != original:
            raise ValueError("Local policy changed during setup; rerun setup.")
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Install and verify selected local masking packs.")
    parser.add_argument("--languages", nargs="+", choices=sorted(PACKS))
    parser.add_argument("--policy", type=Path,
        default=Path(__file__).resolve().parents[2] / ".everwrap-local.json")
    args = parser.parse_args()
    values = args.languages
    if values is None:
        if not sys.stdin.isatty():
            parser.error("Pass --languages en, tr, or en tr in noninteractive setup.")
        print("Available packs: English (en), Turkish (tr). Both have synthetic regression coverage, not guaranteed detection.")
        print("Choose all languages present in your notes, including mixed notes.")
        values = input("Languages [en tr]: ").strip().lower().replace(",", " ").split() or ["en", "tr"]
    try:
        languages = validate_languages(values)
        path = args.policy.resolve()
        original = path.read_bytes()
        SingleNotePolicy.from_file(path)
        uv = shutil.which("uv")
        if not uv:
            raise ValueError("Install uv before running language setup.")
        packages = [package for code in languages for package in PACKS[code]["packages"]]
        subprocess.run([uv, "pip", "install", "--python", sys.executable, *packages], check=True)
        if "tr" in languages:
            from .language import setup_model
            setup_model()
        from .redaction import get_redactor
        redactor = get_redactor(True, languages)
        for code in languages:
            pack = PACKS[code]
            output = redactor.sanitize_text(pack["sample"])
            if ("[PERSON]" not in output or "[LANGUAGE_UNSUPPORTED]" in output
                    or any(word in output for word in pack["private"])):
                raise ValueError("Selected pack failed its fictional masking check; policy was not changed.")
            print(f"{pack['name']} fictional example: {output}")
        save_languages(path, languages, original)
        print("Language selection saved. Access mode, exclusions and date preference preserved. Restart the MCP connection.")
        print("No Evernote notes were read. Unsupported or uncertain passages are withheld; detection remains fallible.")
    except Exception:
        print("Language setup failed. Check uv, network/model installation and a valid local policy with your test note UUID. No raw-note fallback is enabled.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
