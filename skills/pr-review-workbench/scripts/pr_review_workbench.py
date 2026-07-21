#!/usr/bin/env python3
"""Build a bounded PR evidence packet and an offline review workbench."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse


DATASET_STATES = {"complete", "partial", "forbidden", "unsupported", "stale"}
REQUIRED_DATASETS = {"metadata", "files", "checks", "reviews", "source"}
REVIEW_EVENTS = {"APPROVE", "COMMENT", "REQUEST_CHANGES"}
PASSING_CHECKS = {"SUCCESS", "NEUTRAL", "SKIPPED"}


def _safe_url(value: str) -> str:
    parsed = urlparse(value or "")
    return value if parsed.scheme == "https" and parsed.netloc else "#"


def _run(command: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False, timeout=timeout)


def _dataset_blockers(datasets: dict[str, str]) -> list[str]:
    blockers = []
    for name in sorted(REQUIRED_DATASETS - set(datasets)):
        blockers.append(f"{name}: partial")
    for name, state in sorted(datasets.items()):
        if state not in DATASET_STATES:
            raise ValueError(f"invalid dataset state for {name}: {state}")
        if state != "complete":
            blockers.append(f"{name}: {state}")
    return blockers


def _normalize_pr(raw: dict[str, Any], repository: dict[str, str]) -> dict[str, Any]:
    datasets = dict(raw.get("datasets") or {})
    blockers = _dataset_blockers(datasets)
    start_sha = str(raw.get("start_head_sha") or raw.get("head_sha") or "")
    end_sha = str(raw.get("end_head_sha") or start_sha)
    packet_state = "complete"
    if not start_sha or start_sha != end_sha:
        packet_state = "stale"
        blockers.append("head SHA changed during collection")
    for check in raw.get("checks") or []:
        state = str(check.get("state") or "UNKNOWN").upper()
        if state not in PASSING_CHECKS:
            blockers.append(f"check {check.get('name', 'unknown')}: {state.lower()}")
    files = list(raw.get("files") or [])
    additions = sum(int(item.get("additions") or 0) for item in files)
    deletions = sum(int(item.get("deletions") or 0) for item in files)
    return {
        "repository": repository["nameWithOwner"],
        "number": int(raw["number"]),
        "title": str(raw.get("title") or "Untitled pull request"),
        "url": _safe_url(str(raw.get("url") or "")),
        "author": str(raw.get("author") or "unknown"),
        "updated_at": str(raw.get("updated_at") or ""),
        "base_ref": str(raw.get("base_ref") or ""),
        "head_ref": str(raw.get("head_ref") or ""),
        "head_sha": end_sha,
        "packet_state": packet_state,
        "datasets": datasets,
        "decision_state": "ready for human decision" if not blockers else "not ready",
        "blockers": blockers,
        "files": files,
        "checks": list(raw.get("checks") or []),
        "reviews": list(raw.get("reviews") or []),
        "summary": str(raw.get("summary") or "No authored summary was provided."),
        "behavioral_changes": list(raw.get("behavioral_changes") or []),
        "change_size": {"files": len(files), "additions": additions, "deletions": deletions},
    }


def normalize_repository(raw: dict[str, Any]) -> dict[str, Any]:
    repository = dict(raw.get("repository") or {})
    if not repository.get("nameWithOwner"):
        raise ValueError("repository.nameWithOwner is required")
    items = [_normalize_pr(item, repository) for item in raw.get("pull_requests") or []]
    items.sort(key=lambda item: (item["decision_state"] != "not ready", item["updated_at"], item["number"]))
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repository": {"nameWithOwner": repository["nameWithOwner"], "url": _safe_url(str(repository.get("url") or ""))},
        "pull_requests": items,
    }


def collect_fixture(path: Path | str) -> dict[str, Any]:
    return normalize_repository(json.loads(Path(path).read_text(encoding="utf-8")))


def collect_github(repository: str, *, limit: int = 20, runner: Callable[..., Any] = _run) -> dict[str, Any]:
    """Collect PRs in bounded, separately observable GitHub CLI queries."""
    listed = runner([
        "gh", "pr", "list", "--repo", repository, "--state", "open", "--limit", str(limit),
        "--json", "number,title,url,author,updatedAt,baseRefName,headRefName,headRefOid",
    ], timeout=30)
    if listed.returncode != 0:
        raise RuntimeError(f"GitHub PR list failed: {listed.stderr.strip()}")
    raw_prs = json.loads(listed.stdout)
    collected = []
    for item in raw_prs:
        number = int(item["number"])
        try:
            details = runner([
                "gh", "pr", "view", str(number), "--repo", repository,
                "--json", "files,statusCheckRollup,reviews,headRefOid",
            ], timeout=30)
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            details = subprocess.CompletedProcess([], 1, "", "detail query timed out or returned invalid JSON")
        datasets = {"metadata": "complete", "files": "partial", "checks": "partial", "reviews": "partial", "source": "unsupported"}
        detail_data: dict[str, Any] = {}
        if details.returncode == 0:
            try:
                detail_data = json.loads(details.stdout)
            except json.JSONDecodeError:
                detail_data = {}
            else:
                datasets.update({"files": "complete", "checks": "complete", "reviews": "complete"})
        author = item.get("author") or {}
        collected.append({
            "number": number,
            "title": item.get("title"),
            "url": item.get("url"),
            "author": author.get("login") if isinstance(author, dict) else author,
            "updated_at": item.get("updatedAt"),
            "base_ref": item.get("baseRefName"),
            "head_ref": item.get("headRefName"),
            "start_head_sha": item.get("headRefOid"),
            "end_head_sha": detail_data.get("headRefOid", item.get("headRefOid")),
            "datasets": datasets,
            "files": detail_data.get("files", []),
            "checks": [{"name": c.get("name") or c.get("context"), "state": c.get("conclusion") or c.get("state"), "url": c.get("detailsUrl", "")} for c in detail_data.get("statusCheckRollup", [])],
            "reviews": detail_data.get("reviews", []),
            "summary": "Open the evidence drill-down for source-level review.",
            "behavioral_changes": [],
        })
    return normalize_repository({"repository": {"nameWithOwner": repository, "url": f"https://github.com/{repository}"}, "pull_requests": collected})


def materialization_preview(repository_url: str, head_sha: str, destination: str) -> dict[str, Any]:
    if len(head_sha) != 40 or any(ch not in "0123456789abcdefABCDEF" for ch in head_sha):
        raise ValueError("head SHA must be a 40-character hexadecimal commit")
    if _safe_url(repository_url) == "#" or any(char in repository_url + destination for char in ('"', "'", "\r", "\n")):
        raise ValueError("repository URL must be HTTPS and URL/destination cannot contain quotes or newlines")
    prefix = ["git", "-c", "core.hooksPath=NUL", "-c", "credential.helper="]
    return {
        "credential_policy": "none",
        "environment": {"GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"},
        "commands": [
            prefix + ["clone", "--bare", "--filter=blob:none", "--no-tags", repository_url, destination],
            prefix + ["-C", destination, "fetch", "--depth=1", "origin", head_sha],
            prefix + ["-C", destination, "rev-parse", "FETCH_HEAD"],
            prefix + ["-C", destination, "ls-tree", "-r", "--name-only", head_sha],
        ],
        "expected_head_sha": head_sha,
        "inspection": "Read individual blobs with git show SHA:path; never checkout a worktree.",
        "forbidden": ["checkout", "hooks", "filters", "LFS smudge", "submodules", "builds", "tests", "installs"],
    }


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _render_pr_section(item: dict[str, Any], *, active: bool) -> str:
    blockers = item["blockers"] or ["No blocking evidence gaps detected."]
    facts = [
        f"{item['change_size']['files']} files, +{item['change_size']['additions']} / -{item['change_size']['deletions']}",
        f"Head {item['head_sha'][:12]}",
        f"Checks: {sum(1 for check in item['checks'] if str(check.get('state', '')).upper() in PASSING_CHECKS)}/{len(item['checks'])} passing",
        f"Evidence: {item['packet_state']}",
        str(blockers[0]),
    ][:5]
    role = "role" if active else "kind"
    fact_html = "".join(f'<li data-{role}="primary-fact">{_e(fact)}</li>' for fact in facts)
    blocker_html = "".join(f"<li>{_e(blocker)}</li>" for blocker in blockers)
    claims = []
    for claim in item["behavioral_changes"]:
        anchors = " ".join(
            f'<a href="{_e(_safe_url(str(anchor.get("url") or "")))}">{_e(anchor.get("path"))}:{_e(anchor.get("line"))}</a>'
            for anchor in claim.get("anchors") or []
        ) or "No source anchor"
        claims.append(
            f'<article class="claim"><h3>{_e(claim.get("claim"))}</h3><p>{_e(claim.get("impact"))}</p>'
            f'<p class="proof">Proof: {_e(claim.get("proof_state", "unsupported"))} · {anchors}</p></article>'
        )
    claims_html = "".join(claims) or '<p class="muted">No behavioral claim was asserted; inspect changed files.</p>'
    files_html = "".join(
        f'<li><code>{_e(changed.get("path"))}</code> +{int(changed.get("additions") or 0)} / -{int(changed.get("deletions") or 0)}</li>'
        for changed in item["files"]
    )
    hidden = "" if active else " hidden"
    return f'''<section class="pr-section" id="pr-{item['number']}" data-pr="{item['number']}"{hidden}>
<div class="hero"><p class="muted">PR #{item['number']} · {_e(item['author'])}</p><h1>{_e(item['title'])}</h1>
<h2 class="state" data-{role}="decision-state">{_e(item['decision_state'])}</h2><p>{_e(item['summary'])}</p>
<ul class="facts">{fact_html}</ul><a class="next" data-{role}="next-action" href="#pr-{item['number']}-evidence">Inspect the blocking or highest-impact evidence</a></div>
<div id="pr-{item['number']}-evidence" class="panel"><div class="tabs" role="tablist"><button aria-selected="true" data-tab="impact">Impact</button><button aria-selected="false" data-tab="files">Files</button><button aria-selected="false" data-tab="gaps">Gaps</button></div>
<div data-tab-panel="impact">{claims_html}</div><div data-tab-panel="files" hidden><ul>{files_html}</ul></div><div data-tab-panel="gaps" hidden><ul>{blocker_html}</ul></div>
<p><a href="{_e(item['url'])}">Open the original pull request</a></p></div></section>'''


def render_html(packet: dict[str, Any], *, selected_pr: int | None = None) -> str:
    if not packet.get("pull_requests"):
        raise ValueError("packet has no pull requests")
    if selected_pr is None:
        selected = packet["pull_requests"][0]
    else:
        selected = next((item for item in packet["pull_requests"] if item["number"] == selected_pr), None)
        if selected is None:
            raise ValueError(f"PR #{selected_pr} not found in packet")
    inbox = "".join(
        f'<a class="inbox-card" data-pr-card="{item["number"]}" href="#pr-{item["number"]}"><b>#{item["number"]}</b> {_e(item["title"])}<span>{_e(item["decision_state"])}</span></a>'
        for item in packet["pull_requests"]
    )
    sections = "".join(_render_pr_section(item, active=item["number"] == selected["number"]) for item in packet["pull_requests"])
    csp = _e("default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'")
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer"><meta http-equiv="Content-Security-Policy" content="{csp}">
<title>PR review workbench · {_e(packet['repository']['nameWithOwner'])} #{selected['number']}</title>
<style>
:root{{--bg:#0b1020;--panel:#151c31;--text:#f5f7ff;--muted:#aab5d1;--line:#2a3555;--blue:#65a7ff;--amber:#ffd166;--red:#ff7b85;--green:#63d49a}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.45 system-ui,sans-serif}}a{{color:var(--blue)}}header{{position:sticky;top:0;padding:12px 20px;background:#0b1020e8;border-bottom:1px solid var(--line);z-index:2}}main{{display:grid;grid-template-columns:280px 1fr;min-height:100vh}}nav{{padding:18px;border-right:1px solid var(--line)}}.inbox-card{{display:grid;gap:4px;padding:12px;margin-bottom:8px;background:var(--panel);border-radius:10px;text-decoration:none}}.inbox-card span,.muted{{color:var(--muted)}}section{{padding:22px;max-width:1050px}}.hero{{min-height:calc(100vh - 106px);display:grid;align-content:start;gap:14px}}.state{{font-size:clamp(2rem,5vw,4rem);margin:0;color:var(--amber)}}.facts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;padding:0;list-style:none}}.facts li,.panel,.claim{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}}.next{{display:inline-block;width:max-content;background:var(--blue);color:#07101e;padding:12px 18px;border-radius:10px;font-weight:800;text-decoration:none}}.tabs{{display:flex;gap:8px;flex-wrap:wrap}}button{{background:var(--panel);color:var(--text);border:1px solid var(--line);padding:10px 14px;border-radius:9px}}button[aria-selected="true"]{{border-color:var(--blue)}}[data-tab-panel][hidden]{{display:none}}code{{color:var(--green)}}@media(max-width:760px){{main{{grid-template-columns:1fr}}nav{{border-right:0;border-bottom:1px solid var(--line)}}}}
</style></head><body><header><b>{_e(packet['repository']['nameWithOwner'])}</b> · review inbox · snapshot {_e(packet['generated_at'])}</header>
<main><nav aria-label="Pull request inbox">{inbox}</nav><div>{sections}</div></main>
<script>
function selectPr(number){{document.querySelectorAll('.pr-section').forEach(function(section){{section.hidden=section.dataset.pr!==number}});}}
document.querySelectorAll('[data-pr-card]').forEach(function(card){{card.addEventListener('click',function(){{selectPr(card.dataset.prCard)}})}});
document.querySelectorAll('[data-tab]').forEach(function(button){{button.addEventListener('click',function(){{const section=button.closest('.pr-section');section.querySelectorAll('[data-tab]').forEach(function(b){{b.setAttribute('aria-selected','false')}});section.querySelectorAll('[data-tab-panel]').forEach(function(p){{p.hidden=true}});button.setAttribute('aria-selected','true');section.querySelector('[data-tab-panel="'+button.dataset.tab+'"]').hidden=false;location.hash='pr-'+section.dataset.pr+'-'+button.dataset.tab}})}});
const match=location.hash.match(/^#pr-(\d+)/);if(match){{selectPr(match[1])}};
</script></body></html>'''


def prepare_review(packet: dict[str, Any], number: int, event: str, body: str) -> dict[str, Any]:
    event = event.upper()
    if event not in REVIEW_EVENTS:
        raise ValueError(f"event must be one of {sorted(REVIEW_EVENTS)}")
    pr = next((item for item in packet.get("pull_requests", []) if item["number"] == number), None)
    if not pr:
        raise ValueError(f"PR #{number} not found")
    if pr["packet_state"] != "complete" or pr["decision_state"] != "ready for human decision" or pr["blockers"] or not pr["head_sha"]:
        raise RuntimeError("cannot prepare a review until evidence is ready for human decision")
    body_digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
    target = f"{pr['repository']}#{number}@{pr['head_sha']}:{event}:body-{body_digest}"
    return {"schema_version": 1, "repository": pr["repository"], "number": number, "head_sha": pr["head_sha"], "event": event, "body": body, "confirmation": target, "submitted": False}


def submit_review(draft: dict[str, Any], *, dry_run: bool, confirm: str | None, runner: Callable[..., Any] = _run) -> dict[str, Any]:
    required = {"repository", "number", "head_sha", "event", "body", "confirmation"}
    if required - set(draft) or draft.get("event") not in REVIEW_EVENTS:
        raise ValueError("review draft is missing required fields or has an invalid event")
    expected = f"{draft['repository']}#{draft['number']}@{draft['head_sha']}:{draft['event']}:body-{hashlib.sha256(str(draft['body']).encode('utf-8')).hexdigest()[:12]}"
    if draft["confirmation"] != expected:
        raise RuntimeError("review draft content changed after confirmation was prepared")
    if dry_run:
        return {"status": "dry-run", "target": draft["confirmation"], "event": draft["event"], "body": draft["body"], "head_sha": draft["head_sha"]}
    if confirm != draft["confirmation"]:
        return {"status": "cancelled", "target": draft["confirmation"]}
    current = runner(["gh", "pr", "view", str(draft["number"]), "--repo", draft["repository"], "--json", "headRefOid"], timeout=30)
    if current.returncode != 0:
        raise RuntimeError(f"SHA revalidation failed: {current.stderr.strip()}")
    if json.loads(current.stdout).get("headRefOid") != draft["head_sha"]:
        raise RuntimeError("head SHA changed; regenerate the evidence packet")
    endpoint = f"repos/{draft['repository']}/pulls/{draft['number']}/reviews"
    command = ["gh", "api", "--method", "POST", endpoint, "-f", f"commit_id={draft['head_sha']}", "-f", f"event={draft['event']}", "-f", f"body={draft['body']}"]
    try:
        result = runner(command, timeout=30)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("unknown submission state after timeout; inspect GitHub manually and do not retry automatically") from exc
    if result.returncode != 0:
        raise RuntimeError(f"review submission failed without retry: {result.stderr.strip()}")
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("review was submitted but its response was invalid; inspect GitHub manually") from exc
    return {"status": "submitted", "url": response.get("html_url") or f"https://github.com/{draft['repository']}/pull/{draft['number']}"}


def _write_json(path: str, value: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inbox = sub.add_parser("inbox", help="Collect a normalized repository PR inbox")
    source = inbox.add_mutually_exclusive_group(required=True)
    source.add_argument("--fixture")
    source.add_argument("--repo")
    inbox.add_argument("--limit", type=int, default=20)
    inbox.add_argument("--output", required=True)
    render = sub.add_parser("render", help="Render a self-contained HTML workbench")
    render.add_argument("--packet", required=True)
    render.add_argument("--pr", type=int)
    render.add_argument("--output", required=True)
    prepare = sub.add_parser("prepare-review", help="Create an inert, SHA-pinned review draft")
    prepare.add_argument("--packet", required=True)
    prepare.add_argument("--pr", type=int, required=True)
    prepare.add_argument("--event", choices=sorted(REVIEW_EVENTS), required=True)
    prepare.add_argument("--body", required=True)
    prepare.add_argument("--output", required=True)
    submit = sub.add_parser("submit-review", help="Preview or explicitly submit a review draft")
    submit.add_argument("--draft", required=True)
    submit.add_argument("--confirm")
    submit.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "inbox":
        packet = collect_fixture(args.fixture) if args.fixture else collect_github(args.repo, limit=args.limit)
        _write_json(args.output, packet)
        print(f"Wrote {len(packet['pull_requests'])} PRs to {args.output}")
    elif args.command == "render":
        packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(render_html(packet, selected_pr=args.pr), encoding="utf-8")
        print(f"Wrote offline workbench to {args.output}")
    elif args.command == "prepare-review":
        packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
        draft = prepare_review(packet, args.pr, args.event, args.body)
        _write_json(args.output, draft)
        print(f"Review draft created. Confirmation target: {draft['confirmation']}")
    elif args.command == "submit-review":
        draft = json.loads(Path(args.draft).read_text(encoding="utf-8"))
        result = submit_review(draft, dry_run=args.dry_run, confirm=args.confirm)
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
