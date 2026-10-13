#!/usr/bin/env python3
"""Protected-base, fail-closed TDQ editorial release eligibility (NOT a publisher).

Only real GitHub Actions can write the exact-head contexts. Candidate-controlled
files and PR text are DATA, never executed code or source of release authority.
This gate *also* requires a genuine exact-head APPROVED GitHub review by a
different, allowlisted identity. Reviewer configurations are not inferred.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

import tdq_draft_triage as tdq

REPOSITORY = "CrashyCrash/offbeat-website"
SOURCE_CONTEXT = "TDQ Protected Editorial Source"
REVIEW_CONTEXT = "TDQ Independent Editorial Approval"
REVIEWER_LOGIN = "copilot-pull-request-reviewer[bot]"
BRANCH_RE = re.compile(r"tdq/proof-auto-[0-9a-f]{14}\Z")
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


def gh_api(endpoint):
    command = ["gh", "api", "--hostname", "github.com", endpoint]
    response = subprocess.run(command, capture_output=True, text=True,
                              check=True, timeout=45)
    return json.loads(response.stdout)


def set_status(sha, context, state, explanation):
    """Status is attached to immutable candidate SHA, NOT base GITHUB_SHA."""
    cmd = ["gh", "api", "--hostname", "github.com", "-X", "POST",
           "repos/" + REPOSITORY + "/statuses/" + sha,
           "-f", "state=" + state, "-f", "context=" + context,
           "-f", "description=" + explanation[:135],
           "-f", "target_url=" + os.environ["GITHUB_SERVER_URL"] + "/" +
           REPOSITORY + "/actions/runs/" + os.environ["GITHUB_RUN_ID"]]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=45)


class Structure(HTMLParser):
    """Text-only release: ALL markup tags and attributes must be unchanged."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tokens = []

    def handle_starttag(self, tag, attrs):
        self.tokens.append(("open", tag, tuple(attrs)))

    def handle_startendtag(self, tag, attrs):
        self.tokens.append(("empty", tag, tuple(attrs)))

    def handle_endtag(self, tag):
        self.tokens.append(("close", tag))

    def handle_decl(self, declaration):
        # A changed DOCTYPE can switch modern rendering into quirks mode.
        self.tokens.append(("declaration", declaration))

    def unknown_decl(self, declaration):
        self.tokens.append(("other-declaration", declaration))


def text_line_budget(before, after):
    lines = difflib.unified_diff(
        before.decode("utf-8", "strict").splitlines(),
        after.decode("utf-8", "strict").splitlines(), n=0)
    additions = deletions = 0
    for line in lines:
        if line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
    if additions > 60 or deletions > 60 or additions + deletions > 100:
        raise ValueError("editorial release exceeded total edited line budget")
    return additions, deletions


def text_only_and_low_risk(before, after):
    old, new = Structure(), Structure()
    old.feed(before.decode("utf-8", "strict"))
    new.feed(after.decode("utf-8", "strict"))
    if old.tokens != new.tokens:
        raise ValueError("editorial release changed HTML structure or attributes")
    # Raw CSS blocks and source comments aren't source-text editorial changes.
    # TDQ already protects executable script blocks; do not leave inline
    # <style> as an unguarded executable/appearance surface.
    for marker in ("style", "template", "svg"):
        rx = re.compile(r"(?is)<" + marker + r"\b[^>]*>.*?</" + marker + r"\s*>")
        if rx.findall(before.decode("utf-8", "strict")) != rx.findall(after.decode("utf-8", "strict")):
            raise ValueError("protected non-editorial embedded source changed")
    # An SEO-only metadata edit is not sufficient visitor-facing value.
    main_rx = re.compile(r"(?is)<main\b[^>]*>(.*?)</main\s*>")
    old_main = main_rx.findall(before.decode("utf-8", "strict"))
    new_main = main_rx.findall(after.decode("utf-8", "strict"))
    if len(old_main) != 1 or len(new_main) != 1 or old_main == new_main:
        raise ValueError("no demonstrable reader-visible main content improvement")
    # Existing protected TDQ analyzer also refuses link, media, scripts, forms,
    # event handlers and stylesheets, independently of this stronger guard.
    result = tdq.analyze(before, after, "index.html")
    if result["risk_lines"] or result["structured_data_changed"]:
        raise ValueError("new factual/commercial claim risk needs stronger review")
    text_line_budget(before, after)
    return result


def qualified_approver(reviews, sha, author):
    if len(reviews) >= 100:
        return False
    latest = {}
    for r in reviews:
        user = r.get("user") or {}
        login = user.get("login")
        state = r.get("state")
        if isinstance(login, str) and isinstance(state, str):
            latest[login] = r
    # A later change-request or dismissed approval always blocks.
    if any(r.get("state") == "CHANGES_REQUESTED" for r in latest.values()):
        return False
    record = latest.get(REVIEWER_LOGIN)
    return (REVIEWER_LOGIN != author and bool(record)
            and record.get("state") == "APPROVED"
            and record.get("commit_id") == sha
            and (record.get("user") or {}).get("type") == "Bot")


def exact_source(pr, sha):
    if pr.get("number") is None:
        raise ValueError("missing PR identity")
    if pr.get("state") != "open":
        raise ValueError("candidate must be an open PR")
    head, base = pr.get("head") or {}, pr.get("base") or {}
    if (head.get("sha") != sha or not BRANCH_RE.fullmatch(head.get("ref") or "")
            or (head.get("repo") or {}).get("full_name") != REPOSITORY
            or base.get("ref") != "main"
            or (base.get("repo") or {}).get("full_name") != REPOSITORY):
        raise ValueError("PR identity/branch mismatch")
    main = gh_api("repos/" + REPOSITORY + "/git/ref/heads/main")["object"]["sha"]
    if base.get("sha") != main or not SHA_RE.fullmatch(main):
        raise ValueError("candidate base is not current protected main")
    number = pr["number"]
    subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "fetch", "--no-tags",
                    "origin", "refs/pull/%d/head" % number],
                   check=True, capture_output=True, timeout=60)
    head_fetch = tdq.git("rev-parse", "FETCH_HEAD").decode().strip()
    if head_fetch != sha:
        raise ValueError("PR head moved during protected fetch")
    subprocess.run(["git", "merge-base", "--is-ancestor", main, sha],
                   check=True, capture_output=True, timeout=20)
    rows = tdq.git("diff", "--no-renames", "--name-status", main, sha,
                   "--").decode().strip().splitlines()
    paths = tdq.bounded_paths(rows)
    if len(paths) != 1:
        raise ValueError("standing autonomous editorial grant is one page only")
    path = paths[0]
    before, after = tdq.git("show", main + ":" + path), tdq.git("show", sha + ":" + path)
    metrics = text_only_and_low_risk(before, after)
    if max(len(before), len(after)) > 350_000:
        raise ValueError("editorial source size exceeds bounded source budget")
    if gh_api("repos/" + REPOSITORY + "/git/ref/heads/main")["object"]["sha"] != main:
        raise ValueError("protected main moved during analysis")
    if gh_api("repos/" + REPOSITORY + "/pulls/" + str(number))["head"]["sha"] != sha:
        raise ValueError("candidate moved during analysis")
    return path


def selftest():
    good = [{"user": {"login": REVIEWER_LOGIN, "type": "Bot"},
             "state": "APPROVED", "commit_id": "a" * 40}]
    assert qualified_approver(good, "a" * 40, "CrashyCrash")
    assert not qualified_approver(good, "b" * 40, "CrashyCrash")
    assert not qualified_approver(good, "a" * 40, REVIEWER_LOGIN)
    assert not qualified_approver(good + [
        {"user": {"login": REVIEWER_LOGIN, "type": "Bot"},
         "state": "DISMISSED", "commit_id": "a" * 40}],
        "a" * 40, "CrashyCrash")
    assert not qualified_approver(good + [
        {"user": {"login": "someone", "type": "User"},
         "state": "CHANGES_REQUESTED"}], "a" * 40, "CrashyCrash")
    a = b'<html><body><main><p>Guaranteed.</p></main></body></html>'
    b = b'<html><body><main><p>More realistic guidance.</p></main></body></html>'
    text_only_and_low_risk(a, b)
    for other in (b'<!DOCTYPE html><html><body><main><p>More realistic guidance.</p></main></body></html>',
                  b'<html><body><main><div>More realistic guidance.</div></main></body></html>',
                  b'<html><body><main><p class="new">Better.</p></main></body></html>',
                  b'<html><body><main><p>Guaranteed $250 profit.</p></main></body></html>'):
        try:
            text_only_and_low_risk(a, other)
        except ValueError:
            pass
        else:
            raise AssertionError("unapproved source risk must block")
    try:
        text_line_budget(b"<main>" + b"\n".join([b"Old"] * 80) + b"</main>",
                         b"<main>Short.</main>")
    except ValueError:
        pass
    else:
        raise AssertionError("large deletions must never evade the line budget")
    print("TDQ_RELEASE_GATE_SELFTEST_OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--pr", type=int)
    ap.add_argument("--expected-head")
    args = ap.parse_args()
    selftest()
    if args.self_test:
        return 0
    if (not args.pr or args.pr < 1 or not isinstance(args.expected_head, str)
            or not SHA_RE.fullmatch(args.expected_head)
            or os.environ.get("GITHUB_REPOSITORY") != REPOSITORY):
        raise ValueError("invalid protected workflow binding")
    sha = args.expected_head
    # In the event of any internal error the last status is failure/pending,
    # never success; publish a success ONLY after the full independent policy.
    set_status(sha, SOURCE_CONTEXT, "pending", "Protected exact-head source check running")
    set_status(sha, REVIEW_CONTEXT, "pending", "Independent review check running")
    source_ok = False
    try:
        pr = gh_api("repos/" + REPOSITORY + "/pulls/" + str(args.pr))
        if pr["head"]["sha"] != sha:
            raise ValueError("event and current PR head differ")
        path = exact_source(pr, sha)
        set_status(sha, SOURCE_CONTEXT, "success", "Protected text-only source verified: " + path)
        source_ok = True
        # Source eligibility is observable while the credentialless K11
        # candidate is still draft. A separate trusted workflow job can ask
        # Copilot for review without removing the draft backlog reservation.
        if pr.get("draft") is not False:
            raise ValueError("independent approval required before leaving draft")
        reviews = gh_api("repos/" + REPOSITORY + "/pulls/" + str(args.pr) + "/reviews?per_page=100")
        if not qualified_approver(reviews, sha, (pr.get("user") or {}).get("login")):
            raise ValueError("current exact-head separate approving reviewer absent")
        # Recheck both immutable bindings after potentially expensive evaluation.
        if gh_api("repos/" + REPOSITORY + "/git/ref/heads/main")["object"]["sha"] != pr["base"]["sha"]:
            raise ValueError("main changed after independent review")
        if gh_api("repos/" + REPOSITORY + "/pulls/" + str(args.pr))["head"]["sha"] != sha:
            raise ValueError("candidate changed after independent review")
        set_status(sha, REVIEW_CONTEXT, "success", "Non-author Copilot APPROVED exact current source")
        return 0
    except Exception as exc:
        kind = type(exc).__name__
        if not source_ok:
            set_status(sha, SOURCE_CONTEXT, "failure", "Source check failed closed: " + kind)
        set_status(sha, REVIEW_CONTEXT, "failure", "Independent release gate blocked: " + kind)
        print("TDQ_RELEASE_BLOCKED: " + kind + ": " + str(exc)[:160], file=sys.stderr)
        return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        print("TDQ_RELEASE_GATE_ERROR " + type(exc).__name__, file=sys.stderr)
        sys.exit(2)
