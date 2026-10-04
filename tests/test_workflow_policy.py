#!/usr/bin/env python3
"""Keep the workflows on the same Actions policy as openpath.

- every `uses:` is pinned to the commit SHA in .github/actions-policy.json, with a
  `# vX[.Y.Z]` comment of the reviewed major version, and the policy lists no unused action;
- checkout never persists credentials, and no workflow asks for write permissions,
  uses secrets, or runs on pull_request_target;
- the jobs that the main ruleset requires (`brew audit`, `release check`) exist in a
  pull request workflow without path filters or a job-level `if:`, because a skipped
  job reports success and the openpath release relies on these names for auto-merge.

Workflows are read line by line, so these checks assume the 2-space block style used here.
"""
from __future__ import annotations

import json
import pathlib
import re
import unittest
from typing import Dict, List

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((ROOT / '.github' / 'workflows').glob('*.yml'))
POLICY = ROOT / '.github' / 'actions-policy.json'
CI = ROOT / '.github' / 'workflows' / 'ci.yml'
REQUIRED_CHECKS = ('brew audit', 'release check')

USES = re.compile(r' *(?:- +)?uses: *(?P<spec>\S+)(?: *# *(?P<comment>\S+))? *')
PINNED = re.compile(r'(?P<identity>[A-Za-z0-9._-]+/[A-Za-z0-9._-]+)@(?P<sha>[0-9a-f]{40})')
VERSION_COMMENT = re.compile(r'v(?P<major>[0-9]+)(?:\.[0-9]+){0,2}')
CHECKOUT = 'actions/checkout'
JOB_INDENT = 2
JOB_KEY_INDENT = 4


def _lines(path: pathlib.Path) -> List[str]:
    return path.read_text(encoding='utf-8').splitlines()


def _code(line: str) -> str:
    return line.split('#', 1)[0].rstrip()


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(' '))


def _top_level_block(lines: List[str], key: str) -> List[str]:
    for index, line in enumerate(lines):
        if _code(line) == key + ':':
            block: List[str] = []
            for child in lines[index + 1:]:
                if _code(child) and _indent(child) == 0:
                    break
                block.append(child)
            return block
    return []


def _jobs(lines: List[str]) -> Dict[str, List[str]]:
    """Map each job id to the keys directly under it, as `key: value` code."""
    jobs: Dict[str, List[str]] = {}
    current: List[str] = []
    for line in _top_level_block(lines, 'jobs'):
        code = _code(line)
        if not code.strip():
            continue
        if _indent(line) == JOB_INDENT:
            current = jobs.setdefault(code.strip().rstrip(':'), [])
        elif _indent(line) == JOB_KEY_INDENT:
            current.append(code.strip())
    return jobs


class ActionsPinTest(unittest.TestCase):
    def test_every_action_is_pinned_to_the_reviewed_sha(self):
        policy = json.loads(POLICY.read_text(encoding='utf-8'))
        self.assertEqual(policy['schema_version'], 'github-actions-policy-v1')
        reviewed = {entry['identity']: entry for entry in policy['actions']}
        used = set()
        for workflow in WORKFLOWS:
            for number, line in enumerate(_lines(workflow), start=1):
                match = USES.fullmatch(line)
                if match is None:
                    self.assertNotIn('uses:', _code(line), f'{workflow.name}:{number}: unreadable uses')
                    continue
                with self.subTest(workflow=workflow.name, line=number):
                    pinned = PINNED.fullmatch(match.group('spec'))
                    self.assertIsNotNone(pinned, 'pin actions to a full commit SHA')
                    assert pinned is not None
                    entry = reviewed.get(pinned.group('identity'))
                    self.assertIsNotNone(entry, 'add the action to .github/actions-policy.json')
                    assert entry is not None
                    self.assertEqual(pinned.group('sha'), entry['sha'])
                    comment = VERSION_COMMENT.fullmatch(match.group('comment') or '')
                    self.assertIsNotNone(comment, 'add a `# vX.Y.Z` comment')
                    assert comment is not None
                    self.assertEqual('v' + comment.group('major'), entry['reviewed_upstream_ref'])
                    used.add(pinned.group('identity'))
        self.assertEqual(used, set(reviewed), 'the policy must not list unused actions')


class PermissionTest(unittest.TestCase):
    def test_workflows_stay_read_only(self):
        for workflow in WORKFLOWS:
            text = workflow.read_text(encoding='utf-8')
            lines = _lines(workflow)
            with self.subTest(workflow=workflow.name):
                self.assertEqual([_code(line).strip() for line in _top_level_block(lines, 'permissions')
                                  if _code(line).strip()], ['contents: read'])
                self.assertNotRegex(text, r'(?m)^[^#\n]*:\s*write\b')
                self.assertNotIn('write-all', text)
                self.assertNotIn('pull_request_target', text)
                self.assertNotIn('secrets.', text)

    def test_checkout_does_not_persist_credentials(self):
        for workflow in WORKFLOWS:
            codes = [_code(line).strip() for line in _lines(workflow)]
            checkouts = sum(code.startswith(('uses: ' + CHECKOUT + '@', '- uses: ' + CHECKOUT + '@'))
                            for code in codes)
            with self.subTest(workflow=workflow.name):
                self.assertEqual(codes.count('persist-credentials: false'), checkouts)


class RequiredCheckTest(unittest.TestCase):
    def test_required_jobs_always_report(self):
        lines = _lines(CI)
        triggers = [_code(line).strip() for line in _top_level_block(lines, 'on') if _code(line).strip()]
        self.assertIn('pull_request:', triggers)
        self.assertFalse([t for t in triggers if t.startswith(('paths:', 'paths-ignore:'))])

        names = {}
        for job, keys in _jobs(lines).items():
            name = next((key.split(':', 1)[1].strip().strip('"\'') for key in keys if key.startswith('name:')), job)
            names[name] = keys
        for check in REQUIRED_CHECKS:
            with self.subTest(check=check):
                self.assertIn(check, names)
                self.assertFalse([key for key in names[check] if key.startswith('if:')],
                                 'a skipped required job reports success')


if __name__ == '__main__':
    unittest.main()
