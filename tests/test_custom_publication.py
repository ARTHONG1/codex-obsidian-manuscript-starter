import importlib.util
import sys
import tempfile
import json
import hashlib
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("finalize_custom_publication", SCRIPTS / "finalize_custom_publication.py")
publication = importlib.util.module_from_spec(spec)
sys.modules["finalize_custom_publication"] = publication
spec.loader.exec_module(publication)


class CustomPublicationTests(unittest.TestCase):
    def test_dot_segment_output_with_image_uses_normalized_asset_paths(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            image = base / 'image.png'
            Image.new('RGB', (30,20), 'blue').save(image)
            data = {'blocks':[{'component':'image','asset_id':'x','caption':'Sample'}], 'assets':[{'id':'x','path':'image.png','sha256':hashlib.sha256(image.read_bytes()).hexdigest()}]}
            result = publication.finalize_custom_publication(data, base / 'unused' / '..' / 'v0.1', base / 'desktop', asset_root=base)
            self.assertEqual(result['desktop_export_status'], 'exported')
            self.assertEqual(publication.validate_custom_package(base / 'v0.1')['status'], 'ready')

    def test_editorial_review_rejects_private_path_before_render(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'v0.1'
            data = {'blocks':[], 'assets':[{'id':'x','editorial_review':{'prompt':'C:/private/input.png'}}]}
            with self.assertRaisesRegex(ValueError, 'custom_editorial_review_invalid'):
                publication.finalize_custom_publication(data, root)
            self.assertFalse(root.exists())

    def test_modified_output_cannot_be_rehashed_into_valid_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'v0.1'
            publication.finalize_custom_publication({'title':'title','blocks':[]}, root)
            snapshot = {'snapshot_verified':True, 'template_id':'c-test', 'version':'t0.1', 'files':{}, 'template':{'blocks':[]}}
            for name in ('manuscript.md', 'manuscript.html', 'manuscript.pdf'):
                with self.subTest(name=name):
                    files = {p.name:p.read_bytes() for p in root.iterdir() if p.name != 'finalization-report.json'}
                    files[name] += b' altered'
                    report = json.loads(files['custom-validation.json'])
                    report['template'] = {'template_id':'c-test','version':'t0.1','files':{}}
                    report['files'][name] = hashlib.sha256(files[name]).hexdigest()
                    files['custom-validation.json'] = json.dumps(report).encode()
                    with mock.patch.object(publication, 'resolve_template', return_value=snapshot):
                        with self.assertRaisesRegex(ValueError, 'custom_render_mismatch'):
                            publication.validate_custom_snapshot(list(files.items()), 'unused.json')

    def test_dotdot_nested_desktop_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'v0.1'
            destination = Path(directory) / 'unused' / '..' / 'v0.1' / 'desktop'
            with self.assertRaisesRegex(ValueError, 'custom_output_overlap'):
                publication.finalize_custom_publication({'title':'title','blocks':[]}, root, destination)
            self.assertFalse(root.exists())

    def test_finalizer_pins_selected_template_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'v0.1'
            snapshot = {'snapshot_verified': True, 'template_id': 'c-test', 'version': 't0.2', 'files': {}, 'template': {'blocks': []}}
            with mock.patch.object(publication, 'resolve_template', return_value=snapshot) as resolve, mock.patch.object(publication.publisher, 'publish_version', return_value={'status':'published'}):
                publication.finalize_custom_publication({'title':'title','blocks':[]}, root, runtime_config='unused.json', vault_relative_version_dir='03 Custom Manuscript/topic/v0.1', template_name='test', template_version='t0.2')
            resolve.assert_called_once_with('unused.json', 'test', None, version='t0.2')
            self.assertEqual(publication.validate_custom_package(root)['template']['version'], 't0.2')

    def test_approved_image_template_end_to_end_vault_and_desktop(self):
        from PIL import Image
        from pypdf import PdfReader
        import resolve_custom_template as resolver
        from tests.test_template_registration import RegistrationTests, FakeRest, registration
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            helper = RegistrationTests()
            candidate = helper.candidate(root)
            template_path = candidate / 'template.json'
            template = json.loads(template_path.read_text())
            template.pop('candidate_id')
            template['blocks'] = [{'component':'paragraphs'}, {'component':'image'}]
            analysis = json.loads((candidate / 'source-analysis.json').read_text())
            preview = json.loads((candidate / 'preview-content.json').read_text())
            canonical = json.dumps({'schema_version':1,'analysis':analysis,'template':template,'preview':preview}, ensure_ascii=False, sort_keys=True, separators=(',',':'))
            template['candidate_id'] = 'c-' + hashlib.sha256(canonical.encode()).hexdigest()[:16]
            template_path.write_text(json.dumps(template), encoding='utf-8')
            fake = FakeRest()
            with mock.patch.dict('os.environ', {'CODEX_OBSIDIAN_STATE_ROOT': str(root / 'state')}):
                approval = helper.approval(candidate, root / 'state')
                registration.register_candidate({}, candidate, approval, transport=fake)
            image = root / 'figure.png'
            Image.new('RGB', (80,40), 'blue').save(image)
            review = {'method':'generated_scene','prompt':'Synthetic blue sample','visual_kind':'result_preview','privacy_status':'cleared','quality_review':{'relevant':True,'professional':True,'legible':True,'artifact_free':True,'no_generic_ai_motifs':True,'note':'Synthetic test visual'}}
            data = {'title':'Synthetic', 'blocks':[{'component':'paragraphs','text':'Sample text'}, {'component':'image','asset_id':'figure','caption':'Sample figure'}], 'assets':[{'id':'figure','path':'figure.png','sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'editorial_review':review}]}
            with mock.patch.object(resolver, '_RestTransport', return_value=fake), mock.patch.object(publication.publisher, 'list_vault_directory', side_effect=fake.list), mock.patch.object(publication.publisher, 'save_and_verify', side_effect=fake.save):
                result = publication.finalize_custom_publication(data, root / 'v0.1', root / 'desktop', 'unused.json', '03 Custom Manuscript/topic/v0.1', template_name='A', asset_root=root)
            self.assertEqual(result['vault_publication_status'], 'published', result)
            self.assertEqual(result['desktop_export_status'], 'exported', result)
            self.assertEqual(publication.validate_custom_package(root / 'desktop')['assets'][0]['editorial_review'], review)
            self.assertTrue(any(page.images for page in PdfReader(root / 'desktop/manuscript.pdf').pages))
            for path in (root / 'desktop/assets').iterdir():
                self.assertEqual(path.read_bytes(), fake.files['03 Custom Manuscript/topic/v0.1/assets/' + path.name])
            original_listing = publication.publisher._version_files
            def mutate_before_snapshot(version_root):
                paths = original_listing(version_root)
                (version_root / 'manuscript.html').write_text('tampered', encoding='utf-8')
                return paths
            with mock.patch.object(resolver, '_RestTransport', return_value=fake), mock.patch.object(publication.publisher, 'list_vault_directory', side_effect=fake.list), mock.patch.object(publication.publisher, 'save_and_verify', side_effect=fake.save), mock.patch.object(publication.publisher, '_version_files', side_effect=mutate_before_snapshot):
                rejected = publication.finalize_custom_publication(data, root / 'v0.2', runtime_config='unused.json', vault_relative_version_dir='03 Custom Manuscript/topic/v0.2', template_name='A', asset_root=root)
            self.assertEqual(rejected['vault_publication_status'], 'publication_failed')
            self.assertFalse(any(path.startswith('03 Custom Manuscript/topic/v0.2/') for path in fake.files))

    def test_direct_unbound_custom_publish_is_blocked_before_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'v0.1'
            publication.finalize_custom_publication({'title':'title','blocks':[]}, root)
            writes = []
            with mock.patch.object(publication.publisher, 'list_vault_directory', return_value=None), mock.patch.object(publication.publisher, 'save_and_verify', side_effect=lambda *a: writes.append(a)):
                with self.assertRaisesRegex(ValueError, 'custom_template_required'):
                    publication.publisher.publish_version(Path('unused.json'), root, '03 Custom Manuscript/topic/v0.1')
            self.assertEqual(writes, [])

    def test_nested_desktop_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'v0.1'
            with self.assertRaisesRegex(ValueError, 'custom_output_overlap'):
                publication.finalize_custom_publication({'title':'title','blocks':[]}, root, root / 'desktop')
            self.assertFalse(root.exists())

    def test_real_publisher_failure_report_is_sanitized(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'v0.1'
            snapshot = {'snapshot_verified': True, 'template_id': 'c-test', 'version': 't0.1', 'files':{}, 'template': {'blocks': []}}
            with mock.patch.object(publication, 'resolve_template', return_value=snapshot), mock.patch.object(publication.publisher, 'list_vault_directory', side_effect=ConnectionError('SECRET_PRIVATE_PATH')):
                publication.finalize_custom_publication({'title':'title','blocks':[]}, root, runtime_config='unused.json', vault_relative_version_dir='03 Custom Manuscript/topic/v0.1', template_name='test')
            for path in root.glob('*.json'):
                self.assertNotIn('SECRET_PRIVATE_PATH', path.read_text(encoding='utf-8'))

    def test_publication_failure_preserves_verified_desktop_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = {'snapshot_verified': True, 'template_id': 'c-test', 'version': 't0.1', 'template': {'blocks': []}}
            with mock.patch.object(publication, 'resolve_template', return_value=snapshot), mock.patch.object(publication.publisher, 'publish_version', side_effect=ConnectionError('private error')):
                result = publication.finalize_custom_publication({'title':'title','blocks':[]}, root / 'v0.1', root / 'desktop', 'unused.json', '03 Custom Manuscript/topic/v0.1', template_name='test')
            self.assertEqual(result['vault_publication_status'], 'publication_failed')
            self.assertEqual(result['desktop_export_status'], 'exported')
            self.assertEqual(result['status'], 'finalized_with_failure')
            self.assertNotIn('private error', json.dumps(result))
            self.assertEqual(publication.validate_custom_package(root / 'desktop')['status'], 'ready')

    def test_existing_empty_output_folder_is_rejected_as_version_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'v0.1'
            root.mkdir()
            with self.assertRaisesRegex(ValueError, 'custom_output_version_exists'):
                publication.finalize_custom_publication({'title':'title','blocks':[]}, root)

    def test_unexpected_file_cannot_be_included_in_custom_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'v0.1'
            publication.finalize_custom_publication({'title':'title','blocks':[]}, root)
            (root / 'private.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'unexpected_source_file'):
                publication.validate_custom_package(root)

    def test_existing_desktop_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            desktop = root / 'desktop'
            desktop.mkdir()
            old = desktop / 'manuscript.pdf'
            old.write_bytes(b'old user result')
            with self.assertRaisesRegex(ValueError, 'immutable_export_conflict'):
                publication.finalize_custom_publication({'title': 'new', 'blocks': []}, root / 'v0.1', desktop)
            self.assertEqual(old.read_bytes(), b'old user result')
            self.assertEqual(list(desktop.iterdir()), [old])

    def test_report_has_relative_files_and_verified_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = publication.finalize_custom_publication({'title': 'title', 'blocks': []}, root / 'v0.1', root / 'desktop')
            self.assertEqual(result['files']['pdf'], 'manuscript.pdf')
            self.assertTrue((root / 'v0.1/custom-validation.json').exists())
            check = json.loads((root / 'v0.1/custom-validation.json').read_text(encoding='utf-8'))
            self.assertEqual(check['status'], 'ready')
            for name, digest in check['files'].items():
                self.assertEqual(hashlib.sha256((root / 'v0.1' / name).read_bytes()).hexdigest(), digest)
            self.assertEqual((root / 'desktop/manuscript.pdf').read_bytes(), (root / 'v0.1/manuscript.pdf').read_bytes())

    def test_tampered_rendered_file_is_rejected_by_validator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'v0.1'
            publication.finalize_custom_publication({'title': 'title', 'blocks': []}, root)
            (root / 'manuscript.html').write_text('tampered')
            self.assertTrue(callable(getattr(publication, 'validate_custom_package', None)))
            with self.assertRaisesRegex(ValueError, 'asset_hash_mismatch'):
                publication.validate_custom_package(root)

    def test_unapproved_production_is_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'v0.1'
            with self.assertRaisesRegex(ValueError, 'custom_template_required'):
                publication.finalize_custom_publication({'title': 'title', 'blocks': []}, root, runtime_config='unused.json', vault_relative_version_dir='03 Custom Manuscript/topic/v0.1')
            self.assertFalse(root.exists())

    def test_exports_rendered_files_to_desktop_and_separates_vault_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = publication.finalize_custom_publication({"title": "주제", "blocks": []}, root / "v0.1", root / "desktop")
            self.assertEqual(result["vault_publication_status"], "not_attempted")
            self.assertEqual(result["desktop_export_status"], "exported")
            self.assertTrue((root / "desktop" / "manuscript.pdf").exists())


if __name__ == "__main__":
    unittest.main()
