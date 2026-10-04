import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import depgraph_release as release


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tag = "v0.6.1"
        self.sha = "a" * 40
        self.ref = {"object": {"type": "tag", "sha": "b" * 40}}
        self.tag_object = {"object": {"type": "commit", "sha": self.sha},
                           "verification": {"signature": "signed", "reason": "unknown_key"}}
        self.release = {"tag_name": self.tag, "draft": False, "prerelease": False, "assets": []}
        self.evidence = {
            "schema_version": "release-post-publish-evidence-v1", "repository": release.REPOSITORY,
            "tag": self.tag, "release_version": "0.6.1", "decision": "allow",
            "candidate": {"commit": self.sha, "tag_object": "b" * 40},
            "workflow_public_asset_identity": True, "public_download_reverified": True,
            "full_ci": {"run_id": 1, "head_sha": self.sha, "jobs": [{"conclusion": "success"}]},
            "release_workflow": {"run_id": 2, "head_sha": self.sha}, "assets": [],
        }
        self.runs = {}
        for key, name, branch, path, event in (
            ("full_ci", "CI", "main", "ci.yml", "workflow_dispatch"),
            ("release_workflow", "Release", self.tag, "release.yml", "push"),
        ):
            self.runs[key] = {"id": self.evidence[key]["run_id"], "head_sha": self.sha,
                "name": name, "path": ".github/workflows/" + path, "head_branch": branch,
                "event": event, "status": "completed", "conclusion": "success",
                "repository": {"full_name": release.REPOSITORY},
                "head_repository": {"full_name": release.REPOSITORY}}
        for target in release.TARGETS:
            name = f"depgraph-0.6.1-{target}.tar.gz"
            for item in (name, name + ".sha256"):
                self.release["assets"].append({"name": item, "digest": "sha256:" + "c" * 64, "size": 42})
                self.evidence["assets"].append({"name": item, "sha256": "c" * 64, "bytes": 42})

    def validate(self):
        return release.validate(self.tag, self.release, self.evidence, self.ref, self.tag_object, self.runs)

    def test_valid_signed_release(self):
        self.assertEqual(set(self.validate()), set(release.TARGETS))

    def test_rejects_prerelease_unsigned_wrong_commit_and_failed_ci(self):
        for path, value in (
            (("release", "prerelease"), True), (("tag_object", "verification", "signature"), None),
            (("evidence", "candidate", "commit"), "d" * 40),
            (("runs", "full_ci", "conclusion"), "failure"),
            (("runs", "release_workflow", "event"), "pull_request"),
            (("evidence", "decision"), "deny"),
            (("evidence", "public_download_reverified"), False),
            (("runs", "release_workflow", "head_repository", "full_name"), "attacker/fork"),
        ):
            with self.subTest(path=path):
                original = copy.deepcopy(getattr(self, path[0]))
                node = getattr(self, path[0])
                for key in path[1:-1]: node = node[key]
                node[path[-1]] = value
                with self.assertRaises(ValueError): self.validate()
                setattr(self, path[0], original)

    def test_rejects_missing_target_tampered_digest_duplicate_asset(self):
        original = copy.deepcopy(self.release)
        self.release["assets"].pop()
        with self.assertRaises(ValueError): self.validate()
        self.release = copy.deepcopy(original)
        self.release["assets"][0]["digest"] = "sha256:" + "d" * 64
        with self.assertRaises(ValueError): self.validate()
        self.release = copy.deepcopy(original)
        self.release["assets"].append(self.release["assets"][0])
        with self.assertRaises(ValueError): self.validate()

    def test_rejects_noncanonical_tag_and_digest(self):
        for tag in ("v0.6.1-rc1", "v01.2.3", "../../evil", "v0.6.1\n"):
            with self.assertRaises(ValueError): release.version(tag)
        with self.assertRaises(ValueError): release.render(self.tag, dict.fromkeys(release.TARGETS, '"; system("evil")'))

    def test_blocks_downgrades(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "base.rb"
            base.write_text('  version "0.6.1"\n')
            release.no_downgrade("v0.6.1", base)
            release.no_downgrade("v0.6.2", base)
            with self.assertRaises(ValueError): release.no_downgrade("v0.6.0", base)

    def test_render_preserves_package_and_integrity_test(self):
        text = release.render(self.tag, self.validate())
        self.assertNotIn("@VERSION@", text)
        self.assertIn('libexec.install Dir["*"]', text)
        self.assertIn('worker.fetch("integrity")', text)
        self.assertIn('depends_on "node@24"', text)


if __name__ == "__main__":
    unittest.main()
