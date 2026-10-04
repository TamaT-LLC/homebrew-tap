#!/usr/bin/env python3
"""Tests for scripts/check_release.py: verifying the tap cask against its openpath Stable release."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from typing import Dict, Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

import check_release as check  # noqa: E402  (import after the path is set)

VERSION = '0.2.0'
TAG = 'v' + VERSION
ZIP = f'openpath-{VERSION}.zip'
ZIP_BYTES = b'PK\x03\x04 openpath.app stand-in'
URL = 'https://github.com/TamaT-LLC/openpath/releases/download/v#{version}/openpath-#{version}.zip'

# The layout openpath's scripts/cask.sh writes, with the values left open.
CASK_TEMPLATE = '''cask "openpath" do
  version "{version}"
  sha256 "{sha256}"

  url "{url}"
  name "openpath"
  desc "Fuzzy search palette for file open dialogs"
  homepage "https://github.com/TamaT-LLC/openpath"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on macos: {macos}

  app "openpath.app"

  uninstall quit: "jp.tamat.openpath"

  zap trash: [
    "~/.config/openpath",
    "~/Library/Application Support/openpath",
    "~/Library/Logs/openpath",
    "~/Library/Preferences/jp.tamat.openpath.plist",
  ]
end
'''


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cask_text(version: str = VERSION, digest: Optional[str] = None, url: str = URL,
              macos: str = '">= :sonoma"') -> str:
    return CASK_TEMPLATE.format(version=version, sha256=digest or sha256(ZIP_BYTES), url=url, macos=macos)


def release(tag: str = TAG, **fields: object) -> Dict[str, object]:
    """The fields of `GET /repos/{repo}/releases/tags/{tag}` that the check reads."""
    data: Dict[str, object] = {'tag_name': tag, 'draft': False, 'prerelease': False}
    data.update(fields)
    return data


def temp_dir(test: unittest.TestCase) -> pathlib.Path:
    temp = tempfile.TemporaryDirectory(prefix='tap-test-')
    test.addCleanup(temp.cleanup)
    return pathlib.Path(temp.name)


def release_dir(test: unittest.TestCase, cask: Optional[str] = None, zip_bytes: bytes = ZIP_BYTES,
                sums: Optional[str] = None) -> pathlib.Path:
    """A directory laid out like `gh release download` of the Stable assets."""
    path = temp_dir(test)
    cask_bytes = (cask if cask is not None else cask_text()).encode()
    (path / ZIP).write_bytes(zip_bytes)
    (path / 'openpath.rb').write_bytes(cask_bytes)
    if sums is None:
        sums = f'{sha256(zip_bytes)}  {ZIP}\n{sha256(cask_bytes)}  openpath.rb\n'
    (path / 'SHA256SUMS').write_text(sums)
    return path


class ParseCaskTest(unittest.TestCase):
    def test_reads_the_stanzas(self):
        cask = check.parse_cask(cask_text())
        self.assertEqual((cask.version, cask.sha256, cask.url), (VERSION, sha256(ZIP_BYTES), URL))

    def test_rejects_layouts_it_cannot_vouch_for(self):
        digest = sha256(ZIP_BYTES)
        cases = {
            'other token': cask_text().replace('cask "openpath"', 'cask "openpath-preview"'),
            'two versions': cask_text().replace('  sha256', '  version "9.9.9"\n  sha256'),
            'no version': cask_text().replace(f'  version "{VERSION}"\n', ''),
            'version symbol': cask_text().replace(f'"{VERSION}"', ':latest', 1),
            'interpolated version': cask_text(version='#{VERSION}'),
            'no_check': cask_text().replace(f'"{digest}"', ':no_check'),
            'uppercase digest': cask_text(digest=digest.upper()),
            'per-arch digests': cask_text().replace(f'  sha256 "{digest}"',
                                                    f'  sha256 arm: "{digest}", intel: "{digest}"'),
            'two sha256': cask_text().replace('  url', f'  sha256 "{digest}"\n  url', 1),
            'second url': cask_text().replace('  name', '  url "https://example.com/openpath.zip"\n  name'),
            'url symbol only': cask_text().replace(f'  url "{URL}"\n', ''),
            'url with trailing code': cask_text(url=URL + '", verified: "github.com'),
        }
        for name, text in cases.items():
            with self.subTest(name), self.assertRaises(check.ReleaseError):
                check.parse_cask(text)

    def test_tap_cask_in_this_repository_names_a_stable_tag(self):
        cask = check.parse_cask((ROOT / 'Casks' / 'openpath.rb').read_text(encoding='utf-8'))
        self.assertEqual(check.tag_for(cask), 'v' + cask.version)
        self.assertEqual(cask.url, URL)


class TagTest(unittest.TestCase):
    def test_tag_for_a_stable_version(self):
        self.assertEqual(check.tag_for(check.parse_cask(cask_text())), TAG)

    def test_tag_for_rejects_other_versions(self):
        for version in ('0.2.0-preview.1', '0.2', '01.2.3', '0.2.0 '):
            with self.subTest(version=version), self.assertRaisesRegex(check.ReleaseError, 'is not X.Y.Z'):
                check.tag_for(check.parse_cask(cask_text(version=version)))

    def test_only_stable_tags_are_accepted(self):
        for tag in ('preview-v0.2.0-1', '0.2.0', 'v0.2', 'v01.2.3', 'v0.2.0-rc1', 'v0.2.0 ', 'V0.2.0', 'v０.2.0'):
            with self.subTest(tag=tag), self.assertRaisesRegex(check.ReleaseError, 'not a Stable tag'):
                check.parse_stable_tag(tag)


class StableReleaseTest(unittest.TestCase):
    def test_published_stable_passes(self):
        check.check_stable_release(release(), TAG)

    def test_prerelease_and_draft_are_rejected(self):
        cases: Tuple[Dict[str, object], ...] = (
            {'prerelease': True}, {'draft': True}, {'prerelease': None}, {'draft': 'false'})
        for fields in cases:
            data = release()
            data.update(fields)
            with self.subTest(fields=fields), self.assertRaises(check.ReleaseError):
                check.check_stable_release(data, TAG)

    def test_missing_fields_are_rejected(self):
        for field in ('tag_name', 'draft', 'prerelease'):
            data = release()
            del data[field]
            with self.subTest(field=field), self.assertRaises(check.ReleaseError):
                check.check_stable_release(data, TAG)

    def test_release_of_another_tag_is_rejected(self):
        with self.assertRaisesRegex(check.ReleaseError, 'not v0.2.0'):
            check.check_stable_release(release('v0.1.0'), TAG)

    def test_release_json_must_be_an_object(self):
        with self.assertRaises(check.ReleaseError):
            check.check_stable_release([release()], TAG)


class VerifyReleaseTest(unittest.TestCase):
    def test_consistent_release_passes(self):
        result = check.verify_release(release_dir(self), TAG)
        self.assertEqual(result, {'zip_sha256': sha256(ZIP_BYTES),
                                  'release_cask_sha256': sha256(cask_text().encode())})

    def test_tampered_zip_fails(self):
        path = release_dir(self)
        (path / ZIP).write_bytes(ZIP_BYTES + b'tampered')
        with self.assertRaisesRegex(check.ReleaseError, f'SHA-256 of {ZIP} is'):
            check.verify_release(path, TAG)

    def test_tampered_attached_cask_fails(self):
        path = release_dir(self)
        (path / 'openpath.rb').write_text(cask_text().replace('app "openpath.app"', 'app "evil.app"'))
        with self.assertRaisesRegex(check.ReleaseError, 'SHA-256 of openpath.rb is'):
            check.verify_release(path, TAG)

    def test_attached_cask_must_match_the_tag_and_zip(self):
        cases = {
            'version': (cask_text(version='0.1.0'), 'version'),
            'sha256': (cask_text(digest='0' * 64), 'sha256'),
            'url': (cask_text(url=URL.replace('TamaT-LLC/openpath', 'someone/openpath')), 'url'),
        }
        for name, (cask, message) in cases.items():
            with self.subTest(name), self.assertRaisesRegex(check.ReleaseError, f'attached openpath.rb {message}'):
                check.verify_release(release_dir(self, cask=cask), TAG)

    def test_mismatches_are_reported_together(self):
        path = release_dir(self, cask=cask_text(version='0.1.0', digest='0' * 64))
        with self.assertRaises(check.ReleaseError) as raised:
            check.verify_release(path, TAG)
        self.assertIn('does not match tag', str(raised.exception))
        self.assertIn('sha256', str(raised.exception))

    def test_preview_tag_is_rejected(self):
        with self.assertRaisesRegex(check.ReleaseError, 'not a Stable tag'):
            check.verify_release(release_dir(self), 'preview-v0.2.0-1')

    def test_sha256sums_must_list_exactly_the_two_assets(self):
        zip_line = f'{sha256(ZIP_BYTES)}  {ZIP}\n'
        cask_line = f'{sha256(cask_text().encode())}  openpath.rb\n'
        cases = {
            'missing cask': (zip_line, 'must list exactly'),
            'extra entry': (zip_line + cask_line + f'{"1" * 64}  extra.zip\n', 'must list exactly'),
            'duplicate': (zip_line + cask_line + zip_line, 'more than once'),
            'binary marker': (zip_line + cask_line.replace('  ', ' *'), 'line 2'),
            'blank line': (zip_line + '\n' + cask_line, 'line 2'),
            'path': (zip_line + cask_line.replace('openpath.rb', 'dir/openpath.rb'), 'line 2'),
        }
        for name, (sums, message) in cases.items():
            with self.subTest(name), self.assertRaisesRegex(check.ReleaseError, message):
                check.verify_release(release_dir(self, sums=sums), TAG)

    def test_directory_must_hold_exactly_the_assets(self):
        path = release_dir(self)
        (path / 'notes.txt').write_text('unexpected')
        with self.assertRaisesRegex(check.ReleaseError, 'expected exactly'):
            check.verify_release(path, TAG)

        path = release_dir(self)
        (path / ZIP).unlink()
        with self.assertRaisesRegex(check.ReleaseError, 'expected exactly'):
            check.verify_release(path, TAG)

    def test_assets_must_be_nonempty_regular_files(self):
        with self.assertRaisesRegex(check.ReleaseError, 'nonempty regular file'):
            check.verify_release(release_dir(self, zip_bytes=b''), TAG)


class VerifyTapCaskTest(unittest.TestCase):
    def test_cask_identical_to_the_release_passes(self):
        result = check.verify_tap_cask(cask_text(), release(), release_dir(self))
        self.assertEqual(result['tag'], TAG)
        self.assertEqual(result['version'], VERSION)
        self.assertEqual(result['zip_sha256'], sha256(ZIP_BYTES))
        self.assertEqual(result['same_as_release'], 'true')

    def test_cask_edited_outside_the_checked_stanzas_passes(self):
        result = check.verify_tap_cask(cask_text(macos=':sonoma'), release(), release_dir(self))
        self.assertEqual(result['same_as_release'], 'false')

    def test_tap_cask_must_match_the_zip_and_url(self):
        cases = {
            'sha256': cask_text(digest='0' * 64),
            'url': cask_text(url=URL.replace('/v#{version}/', '/preview-v#{version}-1/')),
        }
        for name, cask in cases.items():
            with self.subTest(name), self.assertRaisesRegex(check.ReleaseError, f'tap cask {name}'):
                check.verify_tap_cask(cask, release(), release_dir(self))

    def test_release_must_be_the_one_the_cask_names(self):
        with self.assertRaisesRegex(check.ReleaseError, 'not v0.3.0'):
            check.verify_tap_cask(cask_text(version='0.3.0'), release(), release_dir(self))

    def test_prerelease_is_rejected(self):
        with self.assertRaisesRegex(check.ReleaseError, 'prerelease'):
            check.verify_tap_cask(cask_text(), release(prerelease=True), release_dir(self))

    def test_version_must_not_go_below_the_base_branch(self):
        with self.assertRaisesRegex(check.ReleaseError, 'older than 0.10.0'):
            check.verify_tap_cask(cask_text(), release(), release_dir(self), cask_text(version='0.10.0'))
        for base in ('0.1.9', VERSION):
            with self.subTest(base=base):
                check.verify_tap_cask(cask_text(), release(), release_dir(self), cask_text(version=base))


class CommandLineTest(unittest.TestCase):
    def run_main(self, *argv: str) -> Tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = check.main(list(argv))
        return status, stdout.getvalue(), stderr.getvalue()

    def write(self, name: str, text: str) -> str:
        path = temp_dir(self) / name
        path.write_text(text)
        return str(path)

    def test_tag_prints_the_release_tag(self):
        self.assertEqual(self.run_main('tag', '--cask', self.write('openpath.rb', cask_text())), (0, TAG + '\n', ''))

    def test_verify_prints_github_outputs(self):
        status, stdout, _ = self.run_main(
            'verify', '--cask', self.write('openpath.rb', cask_text()),
            '--release-json', self.write('release.json', json.dumps(release())),
            '--assets', str(release_dir(self)),
            '--base-cask', self.write('base.rb', cask_text(version='0.1.0')))
        self.assertEqual(status, 0)
        self.assertEqual(stdout.splitlines(), [
            f'tag={TAG}', f'version={VERSION}', f'zip_sha256={sha256(ZIP_BYTES)}',
            f'release_cask_sha256={sha256(cask_text().encode())}', 'same_as_release=true'])

    def test_failure_exits_nonzero_without_outputs(self):
        status, stdout, stderr = self.run_main(
            'verify', '--cask', self.write('openpath.rb', cask_text(digest='0' * 64)),
            '--release-json', self.write('release.json', json.dumps(release())),
            '--assets', str(release_dir(self)))
        self.assertEqual((status, stdout), (1, ''))
        self.assertIn('tap cask sha256', stderr)

    def test_unreadable_input_is_a_failure(self):
        status, stdout, stderr = self.run_main('tag', '--cask', '/nonexistent/tap-test.rb')
        self.assertEqual((status, stdout), (1, ''))
        self.assertIn('/nonexistent/tap-test.rb', stderr)

    def test_invalid_release_json_is_a_failure(self):
        status, stdout, stderr = self.run_main(
            'verify', '--cask', self.write('openpath.rb', cask_text()),
            '--release-json', self.write('release.json', '{not json'),
            '--assets', str(release_dir(self)))
        self.assertEqual((status, stdout), (1, ''))
        self.assertIn('error', stderr)


if __name__ == '__main__':
    unittest.main()
