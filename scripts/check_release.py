#!/usr/bin/env python3
"""Verify Casks/openpath.rb against the openpath Stable release it names.

The `release check` job of .github/workflows/ci.yml runs it; it uses the
standard library only.

tag     Prints the release tag (vX.Y.Z) for the version of the tap cask.
verify  Checks, for that tag:
        - the release is a Stable: tag vX.Y.Z, neither a draft nor a prerelease;
        - SHA256SUMS matches the downloaded ZIP and the attached openpath.rb;
        - the version, sha256, and url of both the tap cask and the attached
          cask match the tag and its ZIP;
        - with --base-cask, the version does not go below the base branch.
        It prints tag, version, zip_sha256, release_cask_sha256, and
        same_as_release (whether the tap cask equals the attached one).

Every check fails closed: anything unexpected exits with status 1, so a cask
that does not match its Stable release cannot pass the required check.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import pathlib
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

REPOSITORY = 'TamaT-LLC/openpath'
CASK_TOKEN = 'openpath'
CASK_FILE = 'openpath.rb'
SUMS_FILE = 'SHA256SUMS'
# The url stanza exactly as openpath's scripts/cask.sh writes it; Ruby fills in #{version}.
EXPECTED_URL = 'https://github.com/' + REPOSITORY + '/releases/download/v#{version}/openpath-#{version}.zip'
VERSION = r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)'
STABLE_TAG = re.compile(r'v(?P<version>' + VERSION + r')')
STABLE_VERSION = re.compile(VERSION)
SUMS_LINE = re.compile(r'(?P<digest>[0-9a-f]{64})  (?P<name>[^\s/]+)')
CASK_HEADER = re.compile(r'cask "(?P<token>[^"]*)" do')
QUOTED = re.compile(r'"(?P<value>[^"\\#]*)"')
QUOTED_URL = re.compile(r'"(?P<value>[^"\\]*)"')
QUOTED_SHA256 = re.compile(r'"(?P<value>[0-9a-f]{64})"')
# The livecheck block may point back to the cask url with the symbol `:url`.
LIVECHECK_URL = ':url'
HASH_CHUNK_BYTES = 1024 * 1024
EXIT_FAILURE = 1


class ReleaseError(Exception):
    """A release or cask that must not reach the tap."""


@dataclasses.dataclass(frozen=True)
class Cask:
    version: str
    sha256: str
    url: str


def zip_name(version: str) -> str:
    return f'openpath-{version}.zip'


def parse_stable_tag(tag: str) -> str:
    """Return X.Y.Z of a Stable tag; Preview tags (`preview-v*`) and anything else are rejected."""
    match = STABLE_TAG.fullmatch(tag)
    if match is None:
        raise ReleaseError(f'tag {tag!r} is not a Stable tag of the form vX.Y.Z')
    return match.group('version')


def version_key(version: str) -> Tuple[int, ...]:
    return tuple(int(part) for part in version.split('.'))


def _stanzas(lines: Sequence[str], keyword: str) -> List[str]:
    """Values of every `keyword value` line, at any indentation."""
    pattern = re.compile(r' *' + keyword + r' +(?P<value>.*?) *')
    return [match.group('value') for match in map(pattern.fullmatch, lines) if match]


def _single(lines: Sequence[str], keyword: str) -> str:
    values = _stanzas(lines, keyword)
    if len(values) != 1:
        raise ReleaseError(f'cask must have exactly one {keyword} stanza, found {len(values)}')
    return values[0]


def parse_cask(text: str) -> Cask:
    """Read the stanzas the tap relies on, rejecting any layout the checks cannot vouch for."""
    lines = text.splitlines()
    first = next((line for line in lines if line.strip()), '')
    header = CASK_HEADER.fullmatch(first)
    if header is None or header.group('token') != CASK_TOKEN:
        raise ReleaseError(f'cask must start with `cask "{CASK_TOKEN}" do`')

    version = QUOTED.fullmatch(_single(lines, 'version'))
    if version is None:
        raise ReleaseError('cask version must be a plain quoted string')
    sha256 = QUOTED_SHA256.fullmatch(_single(lines, 'sha256'))
    if sha256 is None:
        raise ReleaseError('cask sha256 must be a quoted lowercase SHA-256 digest')

    urls = [value for value in _stanzas(lines, 'url') if value != LIVECHECK_URL]
    if len(urls) != 1:
        raise ReleaseError(f'cask must have exactly one url stanza with a string, found {len(urls)}')
    url = QUOTED_URL.fullmatch(urls[0])
    if url is None:
        raise ReleaseError('cask url must be a quoted string')
    return Cask(version=version.group('value'), sha256=sha256.group('value'), url=url.group('value'))


def tag_for(cask: Cask) -> str:
    if STABLE_VERSION.fullmatch(cask.version) is None:
        raise ReleaseError(f'cask version {cask.version!r} is not X.Y.Z')
    return 'v' + cask.version


def parse_sums(text: str) -> Dict[str, str]:
    """Parse SHA256SUMS as `shasum -a 256` writes it: `<digest>  <file name>` per line."""
    sums: Dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        match = SUMS_LINE.fullmatch(line)
        if match is None:
            raise ReleaseError(f'{SUMS_FILE} line {number} is not `<sha256>  <file name>`')
        name = match.group('name')
        if name in sums:
            raise ReleaseError(f'{SUMS_FILE} lists {name} more than once')
        sums[name] = match.group('digest')
    return sums


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(HASH_CHUNK_BYTES), b''):
            digest.update(chunk)
    return digest.hexdigest()


def check_stable_release(release: object, tag: str) -> None:
    """The release JSON (`GET /repos/{repo}/releases/tags/{tag}`) must describe a published Stable."""
    if not isinstance(release, dict):
        raise ReleaseError('release JSON must be an object')
    if release.get('tag_name') != tag:
        raise ReleaseError(f'release JSON is for tag {release.get("tag_name")!r}, not {tag}')
    # `is not False` also rejects a missing field, which would otherwise pass as a Stable.
    if release.get('draft') is not False:
        raise ReleaseError(f'release {tag} must have draft: false')
    if release.get('prerelease') is not False:
        raise ReleaseError(f'release {tag} must have prerelease: false')


def _check_files(directory: pathlib.Path, expected: Sequence[str]) -> None:
    found = sorted(path.name for path in directory.iterdir())
    if found != sorted(expected):
        raise ReleaseError(f'expected exactly {sorted(expected)} in {directory}, found {found}')
    for name in expected:
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ReleaseError(f'{name} must be a nonempty regular file')


def _cask_errors(label: str, cask: Cask, version: str, zip_sha256: str) -> List[str]:
    errors = []
    if cask.version != version:
        errors.append(f'{label} version {cask.version!r} does not match tag v{version}')
    if cask.sha256 != zip_sha256:
        errors.append(f'{label} sha256 {cask.sha256} does not match {zip_name(version)} ({zip_sha256})')
    if cask.url != EXPECTED_URL:
        errors.append(f'{label} url {cask.url!r} is not {EXPECTED_URL!r}')
    return errors


def verify_release(directory: pathlib.Path, tag: str) -> Dict[str, str]:
    """Verify the Stable assets of `tag` that `gh release download` saved in `directory`."""
    version = parse_stable_tag(tag)
    archive = zip_name(version)
    _check_files(directory, [archive, CASK_FILE, SUMS_FILE])

    sums = parse_sums((directory / SUMS_FILE).read_text(encoding='utf-8'))
    if sorted(sums) != sorted([archive, CASK_FILE]):
        raise ReleaseError(f'{SUMS_FILE} must list exactly {archive} and {CASK_FILE}, found {sorted(sums)}')
    digests = {name: file_sha256(directory / name) for name in (archive, CASK_FILE)}
    attached = parse_cask((directory / CASK_FILE).read_text(encoding='utf-8'))

    errors = [f'SHA-256 of {name} is {digest}, but {SUMS_FILE} lists {sums[name]}'
              for name, digest in digests.items() if sums[name] != digest]
    errors += _cask_errors(f'attached {CASK_FILE}', attached, version, digests[archive])
    if errors:
        raise ReleaseError('; '.join(errors))
    return {'zip_sha256': digests[archive], 'release_cask_sha256': digests[CASK_FILE]}


def verify_tap_cask(cask_text: str, release: object, directory: pathlib.Path,
                    base_cask_text: Optional[str] = None) -> Dict[str, str]:
    """Verify the tap cask against the release it names, and against the base branch when given."""
    cask = parse_cask(cask_text)
    tag = tag_for(cask)
    check_stable_release(release, tag)
    assets = verify_release(directory, tag)

    errors = _cask_errors('tap cask', cask, cask.version, assets['zip_sha256'])
    if base_cask_text is not None:
        base = parse_cask(base_cask_text)
        tag_for(base)
        if version_key(cask.version) < version_key(base.version):
            errors.append(f'tap cask version {cask.version} is older than {base.version} on the base branch')
    if errors:
        raise ReleaseError('; '.join(errors))

    same = cask_text == (directory / CASK_FILE).read_text(encoding='utf-8')
    return {'tag': tag, 'version': cask.version, **assets, 'same_as_release': 'true' if same else 'false'}


def _report(error: Exception) -> None:
    # Inside GitHub Actions, an error annotation makes the failure visible on the run page.
    prefix = '::error::' if os.environ.get('GITHUB_ACTIONS') == 'true' else 'error: '
    print(f'{prefix}{error}', file=sys.stderr)


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding='utf-8')


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    tag = commands.add_parser('tag', help='print the release tag of the tap cask')
    tag.add_argument('--cask', type=pathlib.Path, required=True)
    verify = commands.add_parser('verify', help='verify the tap cask against its release')
    verify.add_argument('--cask', type=pathlib.Path, required=True)
    verify.add_argument('--release-json', type=pathlib.Path, required=True)
    verify.add_argument('--assets', type=pathlib.Path, required=True)
    verify.add_argument('--base-cask', type=pathlib.Path)
    args = parser.parse_args(argv)

    try:
        if args.command == 'tag':
            print(tag_for(parse_cask(_read(args.cask))))
            return 0
        base = _read(args.base_cask) if args.base_cask else None
        outputs = verify_tap_cask(_read(args.cask), json.loads(_read(args.release_json)), args.assets, base)
    except (ReleaseError, OSError, ValueError) as error:
        _report(error)
        return EXIT_FAILURE

    for key, value in outputs.items():
        print(f'{key}={value}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
