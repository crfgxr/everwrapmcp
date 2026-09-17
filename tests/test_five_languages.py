"""Fictional fixtures for the three additional opt-in packs; never read notes."""
import json
import pytest
from everwrap.packs import PACKS
from everwrap.policy import SingleNotePolicy
from everwrap.redaction import get_redactor

CASES = {
 'es': {
  'plain': 'Me siento estancado en mi trabajo y quiero organizar mis ideas.',
  'names': [('Ayer hablé con Carlos Rodríguez sobre mis planes de trabajo.', ('Carlos','Rodríguez')),
            ('María García trabaja en Microsoft y vive en Madrid.', ('María','García','Microsoft','Madrid'))],
  'phone': 'Teléfono: +34 612 345 678', 'address': 'Dirección: Calle Mayor 25, Madrid',
  'birthday': 'Fecha de nacimiento: 12 de mayo de 1990', 'secret': 'Contraseña: synthetic-pass-927'},
 'fr': {
  'plain': 'Je me sens bloqué au travail et je veux organiser mes idées.',
  'names': [("J'ai discuté de mes projets avec Pierre Martin hier soir.", ('Pierre','Martin')),
            ('Marie Dupont travaille chez Microsoft et habite à Paris.', ('Marie','Dupont','Microsoft','Paris'))],
  'phone': 'Téléphone: +33 6 12 34 56 78', 'address': 'Adresse: 25 rue des Lilas, Paris',
  'birthday': 'Date de naissance: 12 mai 1990', 'secret': 'Mot de passe: synthetic-pass-927'},
 'de': {
  'plain': 'Ich fühle mich bei der Arbeit festgefahren und möchte meine Gedanken ordnen.',
  'names': [('Ich habe mit Thomas Schneider über meine Arbeit gesprochen.', ('Thomas','Schneider')),
            ('Anna Müller arbeitet bei Microsoft und lebt in Berlin.', ('Anna','Müller','Microsoft','Berlin'))],
  'phone': 'Telefon: +49 151 12345678', 'address': 'Adresse: Gartenstraße 25, Berlin',
  'birthday': 'Geburtsdatum: 12. Mai 1990', 'secret': 'Passwort: synthetic-pass-927'},
}

@pytest.mark.parametrize('code', CASES)
def test_installer_sample_and_readability(code):
 r=get_redactor(False,(code,))
 output=r.sanitize_text(PACKS[code]['sample'])
 assert '[PERSON]' in output and 'LANGUAGE_UNSUPPORTED' not in output
 assert all(name not in output for name in PACKS[code]['private'])
 assert r.sanitize_text(CASES[code]['plain']) == CASES[code]['plain']

@pytest.mark.parametrize('code', CASES)
def test_additional_names_organizations_places(code):
 r=get_redactor(False,(code,))
 for text, forbidden in CASES[code]['names']:
  output=r.sanitize_text(text)
  assert 'LANGUAGE_UNSUPPORTED' not in output
  assert all(word not in output for word in forbidden), output

@pytest.mark.parametrize('code', CASES)
def test_local_labels_and_date_preference(code):
 r=get_redactor(False,(code,))
 for category in ('phone','address','secret'):
  output=r.sanitize_text(CASES[code][category])
  assert 'synthetic-pass' not in output and not any(c.isdigit() for c in output)
  assert '[' in output
 assert r.sanitize_text(CASES[code]['birthday']) == CASES[code]['birthday']
 assert '1990' not in get_redactor(True,(code,)).sanitize_text(CASES[code]['birthday'])
 assert 'alex@example.com' not in r.sanitize_text(CASES[code]['plain']+' Email: alex@example.com')

@pytest.mark.parametrize('code', CASES)
def test_single_pack_holds_other_languages(code):
 r=get_redactor(False,(code,))
 for other in CASES:
  if other!=code:
   assert r.sanitize_text(CASES[other]['plain'])=='[LANGUAGE_UNSUPPORTED]'
 assert r.sanitize_text('Voglio organizzare i miei pensieri e migliorare il mio lavoro.')=='[LANGUAGE_UNSUPPORTED]'


def test_all_five_mixed_paragraphs():
 r=get_redactor(False,tuple(sorted(PACKS)))
 text='\n'.join(p['sample'] for p in PACKS.values())
 output=r.sanitize_text(text)
 assert 'LANGUAGE_UNSUPPORTED' not in output
 assert all(name not in output for p in PACKS.values() for name in p['private'])
 assert output.count('[PERSON]')>=5

@pytest.mark.parametrize('code', CASES)
def test_selected_new_pack_persists_and_blocks(tmp_path, code):
 from everwrap.setup import save_languages
 from everwrap.policy import AccessDenied
 path=tmp_path/'policy.json'
 blocked='11111111-2222-3333-4444-555555555555'
 path.write_text(json.dumps({'access_mode':'denylist','blocked_note_ids':[blocked]}))
 save_languages(path,(code,),path.read_bytes())
 p=SingleNotePolicy.from_file(path)
 assert p.languages==(code,)
 with pytest.raises(AccessDenied):p.authorize(blocked)

@pytest.mark.parametrize('code', CASES)
def test_single_pack_does_not_load_other_spacy_packs(code, monkeypatch):
 import importlib
 from everwrap.redaction import PresidioRedactor
 original=importlib.import_module
 loaded=[]
 def guarded(name,*args,**kwargs):
  if name.endswith('_core_news_md'):
   assert name==PACKS[code]['model']
   loaded.append(name)
  return original(name,*args,**kwargs)
 monkeypatch.setattr(importlib,'import_module',guarded)
 PresidioRedactor((code,))
 assert loaded==[PACKS[code]['model']]
