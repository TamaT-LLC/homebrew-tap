#!/usr/bin/env python3
"""Render/verify depgraph formulae from authenticated public release metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

REPOSITORY = "TamaT-LLC/depgraph-cli"
TARGETS = (
    "aarch64-apple-darwin",
    "aarch64-unknown-linux-gnu", "x86_64-unknown-linux-gnu",
)
TAG = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
DIGEST = re.compile(r"sha256:([0-9a-f]{64})\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def version(tag):
    require(bool(TAG.fullmatch(tag)), "expected canonical stable tag vX.Y.Z")
    return tuple(int(part) for part in tag[1:].split("."))


def api(path, binary=False) -> Any:
    command = ["gh", "api"]
    if binary:
        command += ["-H", "Accept: application/octet-stream"]
    result = subprocess.run(command + [f"repos/{REPOSITORY}/{path}"],
                            check=True, stdout=subprocess.PIPE)
    return result.stdout if binary else json.loads(result.stdout)


def inventory(entries):
    result = {}
    for entry in entries:
        name = entry["name"]
        require(name not in result, f"duplicate asset: {name}")
        result[name] = entry
    return result


def asset_digest(asset):
    match = DIGEST.fullmatch(asset.get("digest", ""))
    if match is None:
        raise ValueError(f"missing SHA-256 for {asset['name']}")
    return match.group(1)


def download(asset):
    data = api(f"releases/assets/{asset['id']}", binary=True)
    require(len(data) == asset["size"], f"size mismatch: {asset['name']}")
    require(hashlib.sha256(data).hexdigest() == asset_digest(asset),
            f"digest mismatch: {asset['name']}")
    return data


def validate(tag, release, evidence, tag_ref, tag_object, runs):
    version(tag)
    require(release.get("tag_name") == tag and release.get("draft") is False
            and release.get("prerelease") is False, "not a public stable release")
    require(tag_ref["object"]["type"] == "tag", "tag must be annotated")
    verification = tag_object["verification"]
    require(verification.get("signature") and verification.get("reason") in
            ("valid", "unknown_key", "unverified_email"), "tag must be signed")
    require(tag_object["object"]["type"] == "commit", "tag must point to commit")
    candidate = evidence["candidate"]
    sha = tag_object["object"]["sha"]
    require(candidate["commit"] == sha and candidate["tag_object"] == tag_ref["object"]["sha"],
            "evidence candidate does not match signed tag")
    require(evidence.get("schema_version") == "release-post-publish-evidence-v1"
            and evidence.get("repository") == REPOSITORY and evidence.get("tag") == tag
            and evidence.get("release_version") == tag[1:] and evidence.get("decision") == "allow"
            and evidence.get("workflow_public_asset_identity") is True
            and evidence.get("public_download_reverified") is True, "release evidence denied")
    require(evidence["full_ci"]["jobs"] and all(
        job.get("conclusion") == "success" for job in evidence["full_ci"]["jobs"]),
        "full CI evidence is incomplete")
    for key, name, path, branch in (
        ("full_ci", "CI", ".github/workflows/ci.yml", "main"),
        ("release_workflow", "Release", ".github/workflows/release.yml", tag),
    ):
        claim, run = evidence[key], runs[key]
        require(type(claim["run_id"]) is int and claim["run_id"] > 0, "invalid run id")
        require(claim["head_sha"] == sha and run["id"] == claim["run_id"]
                and run.get("name") == name and run.get("path") == path
                and run.get("head_sha") == sha and run.get("head_branch") == branch
                and run.get("event") in (("push", "workflow_dispatch") if key == "full_ci" else ("push",)) and run.get("status") == "completed"
                and run.get("conclusion") == "success"
                and run["repository"]["full_name"] == REPOSITORY
                and run["head_repository"]["full_name"] == REPOSITORY,
                f"{name} is not a successful canonical run")
    assets, claims = inventory(release["assets"]), inventory(evidence["assets"])
    digests = {}
    for target in TARGETS:
        name = f"depgraph-{tag[1:]}-{target}.tar.gz"
        for item in (name, name + ".sha256"):
            require(item in assets and item in claims, f"missing asset: {item}")
            require(asset_digest(assets[item]) == claims[item]["sha256"]
                    and assets[item]["size"] == claims[item]["bytes"],
                    f"asset differs from public evidence: {item}")
        digests[target] = asset_digest(assets[name])
    return digests


def verified_release(tag):
    version(tag)
    release = api(f"releases/tags/{tag}")
    assets = inventory(release["assets"])
    evidence = json.loads(download(assets[f"release-post-publish-evidence-{tag}.json"]))
    ref = api(f"git/ref/tags/{tag}")
    require(ref["object"]["type"] == "tag", "tag must be annotated")
    tag_object = api(f"git/tags/{ref['object']['sha']}")
    runs = {key: api(f"actions/runs/{evidence[key]['run_id']}")
            for key in ("full_ci", "release_workflow")}
    digests = validate(tag, release, evidence, ref, tag_object, runs)
    for target, digest in digests.items():
        name = f"depgraph-{tag[1:]}-{target}.tar.gz"
        checksum = download(assets[name + ".sha256"]).decode("ascii")
        require(checksum in (f"{digest}  {name}\n", f"{digest} *{name}\n"),
                f"noncanonical checksum: {name}")
    return digests, evidence["release_workflow"]["run_id"]


def render(tag, digests):
    version(tag)
    result = Path(__file__).with_name("depgraph.rb.in").read_text()
    result = result.replace("@VERSION@", tag[1:])
    for target in TARGETS:
        require(bool(re.fullmatch(r"[0-9a-f]{64}", digests[target])), "invalid archive digest")
        result = result.replace(f"@{target}@", digests[target])
    require("@VERSION@" not in result, "unexpanded template")
    return result


def formula_tag(path):
    match = re.search(r'releases/download/v([0-9]+\.[0-9]+\.[0-9]+)/', path.read_text(), re.MULTILINE)
    if match is None:
        raise ValueError("missing formula version")
    tag = "v" + match.group(1)
    version(tag)
    return tag


def no_downgrade(tag, base):
    require(version(tag) >= version(formula_tag(base)), "formula downgrade denied")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("render", "verify"))
    parser.add_argument("--tag")
    parser.add_argument("--formula", type=Path, default=Path("Formula/depgraph.rb"))
    parser.add_argument("--base-formula", type=Path)
    parser.add_argument("--release-run-id", type=int)
    args = parser.parse_args()
    tag = args.tag or formula_tag(args.formula)
    digests, run_id = verified_release(tag)
    if args.release_run_id is not None:
        require(run_id == args.release_run_id, "trigger run differs from public release evidence")
    if args.base_formula and args.base_formula.exists():
        no_downgrade(tag, args.base_formula)
    expected = render(tag, digests)
    if args.command == "render":
        args.formula.parent.mkdir(parents=True, exist_ok=True)
        args.formula.write_text(expected)
    else:
        require(args.formula.read_text() == expected, "formula differs from verified canonical template")
    print(f"{args.command}: depgraph {tag}, signed tag, successful CI/Release, {len(TARGETS)} archive digests verified")


if __name__ == "__main__":
    main()
