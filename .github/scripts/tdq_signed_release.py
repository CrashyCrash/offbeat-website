#!/usr/bin/env python3
"""Protected GitHub gate for K11 independent signed editorial review.

Never execute PR code or trust PR descriptions/agent claims as instructions.
GitHub Actions (not the GPU worker) enforces protected source boundaries,
checks a separate local reviewer's Ed25519 signature, then asks GitHub to
enforce its native branch rules. No Copilot subscription is required.
"""
import base64
import binascii
import difflib
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

import tdq_draft_triage as tdq

REPO = "CrashyCrash/offbeat-website"
RELEASE = "tdq-editorial-release"
HOLD = "tdq-release-hold"
STATUS_LEDGER_ISSUE = 838
STATUS_LEDGER_ENTRY = re.compile(r"TDQ_GREEN_V1 pr=([1-9][0-9]*) head=([0-9a-f]{40})\Z")
SOURCE_STATUS = "TDQ Verified Editorial Source"
REVIEW_STATUS = "TDQ Signed Independent Review"
PUBLIC_KEY = Path(__file__).with_name("reviewer-public.pem")
COMMENT = re.compile(r"<!-- TDQ-SIGNED-REVIEW-V1\n([^\n]{1,8000})\n-->")
BRANCH = re.compile(r"tdq/proof-auto-[0-9a-f]{14}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
# These patterns are additional triage only; no regex proves factual accuracy.
FACT_RISK = re.compile(
    r"(?i)(?:\d|[$%]|\b(?:free|license|lifetime|subscription|price|pricing|"
    r"guarantee|always|never|only|every|best|verified|tested|ranked|"
    r"compatible|ship|deliver|promise|respond|reply|available|"
    r"copyright|monetiz|tomorrow|today|quickly|immediately|"
    r"day|week|month|hour|year|faster|slow|safe|unsafe)\b)"
)


def api(endpoint, method="GET", fields=None):
    cmd = ["gh", "api", "--hostname", "github.com", "-X", method,
           "repos/" + REPO + "/" + endpoint]
    for key, value in (fields or {}).items():
        cmd += ["-f", key + "=" + str(value)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    if p.returncode:
        raise ValueError("trusted GitHub request failed: " + endpoint.split("/")[0])
    return json.loads(p.stdout)


def git(*args):
    return tdq.git(*args).decode("utf-8", "strict").strip()


def status(sha, name, state, description):
    api("statuses/" + sha, "POST", {
        "state": state, "context": name, "description": description[:125],
        "target_url": os.environ["GITHUB_SERVER_URL"] + "/" + REPO +
                      "/actions/runs/" + os.environ["GITHUB_RUN_ID"]
    })


class Structure(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tokens = []

    def handle_starttag(self, tag, attrs):
        self.tokens.append(("start", tag, tuple(attrs)))

    def handle_startendtag(self, tag, attrs):
        self.tokens.append(("empty", tag, tuple(attrs)))

    def handle_endtag(self, tag):
        self.tokens.append(("end", tag))

    def handle_decl(self, decl):
        self.tokens.append(("decl", decl))

    def unknown_decl(self, decl):
        self.tokens.append(("decl-unknown", decl))

    def handle_comment(self, data):
        self.tokens.append(("comment", data))

    def handle_entityref(self, name):
        self.tokens.append(("entity", name))

    def handle_charref(self, name):
        self.tokens.append(("charref", name))


def low_risk_editorial(old, new, path):
    # Do not autonomously rewrite legal notices or owner correspondence
    # promises even when the page otherwise looks like normal HTML.
    if path in ("privacy.html", "disclosure.html", "contact.html", "terms.html"):
        raise ValueError("policy, contact and disclosure pages need stronger approval")
    if len(old) > 350_000 or len(new) > 350_000:
        raise ValueError("oversized HTML source")
    before, after = old.decode("utf-8", "strict"), new.decode("utf-8", "strict")
    a, b = Structure(), Structure()
    a.feed(before)
    b.feed(after)
    if a.tokens != b.tokens:
        raise ValueError("markup attributes, declarations or comments changed")
    for tag in ("style", "svg", "template"):
        rx = re.compile(r"(?is)<" + tag + r"\b[^>]*>.*?</" + tag + r"\s*>")
        if rx.findall(before) != rx.findall(after):
            raise ValueError("protected embedded markup changed")
    main = re.compile(r"(?is)<main\b[^>]*>.*?</main\s*>")
    if len(main.findall(before)) != 1 or len(main.findall(after)) != 1:
        raise ValueError("one reader-visible main content element required")
    if main.findall(before) == main.findall(after):
        raise ValueError("metadata-only edit cannot enter release lane")
    before_main, after_main = main.search(before), main.search(after)
    if (before[:before_main.start()] != after[:after_main.start()]
            or before[before_main.end():] != after[after_main.end():]):
        raise ValueError("autonomous copy release may change ONLY main content")
    report = tdq.analyze(old, new, path)
    if report["structured_data_changed"]:
        raise ValueError("changed structured data requires stronger review")
    # tdq.RISK counts entire ADDED lines, including previously-present words
    # like "free". Do not mistake a correction removing false promises for
    # the INTRODUCTION of a new promise. This is vocabulary triage only;
    # an independent exact-head reviewer must separately substantiate safety.
    add = rem = 0
    changes = []
    added = []
    removed = []
    for line in difflib.unified_diff(before.splitlines(), after.splitlines(), n=0):
        if line.startswith("+") and not line.startswith("+++"):
            add += 1
            changes.append(line[1:])
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            rem += 1
            changes.append(line[1:])
            removed.append(line[1:])
    # Even one changed HTML line may be huge; bound total changed bytes too.
    if add > 40 or rem > 40 or add + rem > 75 or sum(map(len, changes)) > 2500:
        raise ValueError("editorial patch exceeds conservative size budget")
    # Permit removing an unsupported promotional claim only after the
    # separate actual signed semantic reviewer proves this is net beneficial.
    # NEVER allow deletion of required disclosure/legal/accessibility/safety
    # language just because it appears on a normal tutorial page.
    if any(re.search(r"(?i)\b(?:affiliate|disclos\w*|copyright|privacy|"
                     r"consent|refund|terms|accessib\w*|safety|warning)\b", x)
           for x in removed):
        raise ValueError("protected legal/disclosure/safety claim was removed")
    # Reject introduced numbers and risky terms. Previously present
    # vocabulary may be retained in a corrective rewrite, but it is never
    # by itself evidence of factual accuracy.
    removed_text = "\n".join(removed)
    added_text = "\n".join(added)
    def risky_tokens(source):
        numeric = {m.group(0) for m in re.finditer(
            r"\d+(?:[.,]\d+)?", source)}
        without_numbers = re.sub(r"\d+(?:[.,]\d+)?", "", source)
        terms = {m.group(0).casefold() for m in
                 FACT_RISK.finditer(without_numbers)}
        return terms | {"#" + v for v in numeric}
    if risky_tokens(added_text) - risky_tokens(removed_text):
        raise ValueError("new numeric/product/timing/commercial claim needs stronger review")
    return report


class MergedButUnverified(RuntimeError):
    """A real GitHub merge happened but public deployment was NOT proven."""


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def verify_signature(payload, signature):
    if not PUBLIC_KEY.is_file() or len(signature) > 200:
        return False
    try:
        binary = base64.b64decode(signature, validate=True)
    except (ValueError, binascii.Error):
        return False
    if len(binary) != 64:  # Ed25519 signature size.
        return False
    with tempfile.TemporaryDirectory(prefix="tdq-signed-verdict-") as folder:
        data = Path(folder, "payload")
        sig = Path(folder, "signature")
        data.write_bytes(canonical(payload))
        sig.write_bytes(binary)
        p = subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin",
                            "-inkey", str(PUBLIC_KEY), "-rawin",
                            "-in", str(data), "-sigfile", str(sig)],
                           capture_output=True, timeout=12)
        return p.returncode == 0


def signed_review(comments, pr, sha, base, path, now):
    if len(comments) >= 100:
        raise ValueError("review comments exceeded bounded API page")
    valid = []
    for item in comments:
        body = item.get("body") or ""
        matches = COMMENT.findall(body)
        if len(matches) != 1:
            continue
        try:
            envelope = json.loads(matches[0])
            if set(envelope) != {"payload", "signature"}:
                continue
            signed = envelope["payload"]
            if not isinstance(signed, dict) or set(signed) != {
                "schema", "repo", "pr", "head", "base", "paths", "verdict",
                "issued_at", "expires_at", "reviewer", "reason"}:
                continue
            if (signed["schema"] != "tdq-review-v1" or signed["repo"] != REPO
                    or signed["pr"] != pr or signed["head"] != sha
                    or signed["base"] != base or signed["paths"] != [path]
                    or signed["verdict"] not in ("APPROVE", "REJECT")
                    or signed["reviewer"] != "k11-isolated-ollama-review"
                    or not isinstance(signed["reason"], str)
                    or not 30 <= len(signed["reason"]) <= 1500
                    or not isinstance(signed["issued_at"], int)
                    or not isinstance(signed["expires_at"], int)
                    or not signed["issued_at"] <= now + 60
                    or not signed["issued_at"] < signed["expires_at"]
                    or not signed["expires_at"] <= signed["issued_at"] + 21600):
                continue
            if verify_signature(signed, envelope["signature"]):
                # Highest actual SIGNED timestamp wins, not GitHub comment
                # chronology. Reposting an old approved envelope cannot
                # override a newer separately signed REJECT.
                valid.append((signed["issued_at"],
                              signed["verdict"] == "REJECT",
                              signed["verdict"],
                              signed["expires_at"]))
        except (ValueError, TypeError, KeyError, OSError):
            continue
    if not valid:
        return False
    latest = max(valid)
    # An expired later signed REJECT must NEVER be ignored in favor of an
    # older, still-valid APPROVE. Verify ALL signatures first, pick the latest
    # distinct-key verdict (REJECT breaks timestamp ties), and only then
    # check the resulting approval's short-lived authorization window.
    return (latest[2] == "APPROVE"
            and now - 21600 <= latest[0] <= now
            and now < latest[3])


def policy_mode():
    """Preflight under legacy protection; release ONLY under new exact rules.

    Preflight writes trusted source/review statuses on actual K11 signed
    candidates but CANNOT merge or mark ready. This breaks the migration
    chicken-and-egg problem without weakening old DatBotty protections.
    """
    r = api("rulesets/22973860")
    if (r.get("enforcement") != "active" or r.get("target") != "branch"
            or r.get("source") != REPO):
        raise ValueError("active protected-main ruleset not present")
    refs = (r.get("conditions") or {}).get("ref_name") or {}
    # GitHub exclusion rules may use wildcards; no exclusion is acceptable
    # for this dedicated main-only release protection rule.
    if ("refs/heads/main" not in refs.get("include", [])
            or refs.get("exclude")):
        raise ValueError("protected main branch scope changed or excluded")
    checks, pull = None, None
    for rule in r.get("rules") or []:
        if rule.get("type") == "required_status_checks":
            checks = rule.get("parameters")
        if rule.get("type") == "pull_request":
            pull = rule.get("parameters")
    required = {x.get("context"): x.get("integration_id") for x in
                (checks or {}).get("required_status_checks", [])}
    if (not checks or checks.get("strict_required_status_checks_policy") is not True
            or not pull or pull.get("required_review_thread_resolution") is not True
            or pull.get("dismiss_stale_reviews_on_push") is not True):
        raise ValueError("native GitHub branch protection weakened")
    if required == {"DatBotty Deterministic Gate": 15368,
                    "DatBotty T1 Review": 15368}:
        return "PREFLIGHT_ONLY"
    # The RELEASE EXECUTOR must be unable to bypass branch protection.
    # Requiring the entire administration-only bypass_actors list here would
    # deadlock a default GITHUB_TOKEN (that field may be redacted). Owner's
    # existing emergency recovery bypass is NOT used by this workflow.
    # GitHub independently enforces the two required App-bound statuses when
    # current_user_can_bypass is conclusively 'never', not missing/unknown.
    if (required == {SOURCE_STATUS: 15368, REVIEW_STATUS: 15368}
            and r.get("current_user_can_bypass") == "never"):
        return "PROTECTED_RELEASE"
    raise ValueError("unknown or unsafe protected-main policy; do not release")


def check(pr):
    number = pr["number"]
    fresh = api("pulls/" + str(number))
    head, base = fresh["head"], fresh["base"]
    if (fresh.get("state") != "open"
            or head.get("repo", {}).get("full_name") != REPO
            or not BRANCH.fullmatch(head.get("ref") or "")
            or base.get("ref") != "main"
            or RELEASE not in {x.get("name") for x in fresh.get("labels", [])}
            or HOLD in {x.get("name") for x in fresh.get("labels", [])}):
        raise ValueError("unqualified or held TDQ candidate")
    sha, old = head["sha"], base["sha"]
    main = api("git/ref/heads/main")["object"]["sha"]
    if not SHA.fullmatch(sha) or old != main:
        raise ValueError("stale main or invalid immutable head")
    command = ["git", "fetch", "--no-tags", "origin",
               "refs/pull/%d/head" % number]
    subprocess.run(command, check=True, capture_output=True, timeout=65)
    if git("rev-parse", "FETCH_HEAD") != sha:
        raise ValueError("candidate changed during checkout-free git fetch")
    subprocess.run(["git", "merge-base", "--is-ancestor", old, sha],
                   check=True, capture_output=True, timeout=15)
    changed = git("diff", "--no-renames", "--name-status", old, sha, "--")
    paths = tdq.bounded_paths(changed.splitlines())
    if len(paths) != 1:
        raise ValueError("standing release authority is single existing HTML only")
    path = paths[0]
    before = tdq.git("show", old + ":" + path)
    after = tdq.git("show", sha + ":" + path)
    low_risk_editorial(before, after, path)
    comments = api("issues/" + str(number) + "/comments?per_page=100")
    if not signed_review(comments, number, sha, old, path, int(time.time())):
        raise ValueError("no current independent K11 reviewer signed approval")
    return number, sha, old, path


def verify_pages_source():
    pages = api("pages")
    if (pages.get("build_type") != "legacy"
            or pages.get("source") != {"branch": "main", "path": "/"}
            or pages.get("cname") != "offbeatinc.com"):
        raise ValueError("public Pages source no longer main:/ offbeatinc.com")


def finalize(pr, mode):
    number, sha, old, path = check(pr)
    verify_pages_source()
    if policy_mode() != mode:
        raise ValueError("main ruleset changed during candidate check")
    # Only a protected GitHub Actions identity may mint these statuses.
    # Never leave a green release token on an OPEN draft after preflight or
    # a failed native merge; native check state otherwise outlives review TTL.
    native_merged = False
    try:
        # Persist every success-authorized SHA BEFORE minting the first
        # green commit status; closed/renamed PRs remain discoverable.
        register_status_head(number, sha)
        status(sha, SOURCE_STATUS, "success", "Bounded source verified on protected main")
        status(sha, REVIEW_STATUS, "success", "Distinct-key K11 reviewer signature verified")
        if mode != "PROTECTED_RELEASE":
            status(sha, SOURCE_STATUS, "pending", "Preflight proven; native release not authorized")
            status(sha, REVIEW_STATUS, "pending", "Independent review preflight only")
            print("TDQ_PREFLIGHT_SIGNED_STATUSES_PROVEN_NO_MERGE pr=%d head=%s" %
                  (number, sha), flush=True)
            return
        # GITHUB_TOKEN changes do not retrigger workflows. This SAME trusted
        # run marks ready and performs its guarded normal provider merge.
        now = api("pulls/" + str(number))
        if now.get("draft") is True:
            ready = subprocess.run(["gh", "pr", "ready", str(number),
                                    "-R", REPO], capture_output=True,
                                   text=True, timeout=35)
            if ready.returncode:
                raise ValueError("provider refused approved draft transition")
        if check(pr)[:3] != (number, sha, old):
            raise ValueError("candidate or signed review changed before merge")
        if policy_mode() != "PROTECTED_RELEASE":
            raise ValueError("protected release authority removed before merge")
        result = api("pulls/" + str(number) + "/merge", "PUT", {
            "sha": sha, "merge_method": "merge",
            "commit_title": "Protected signed local TDQ editorial release (#%d)" % number})
        if not result.get("merged") or not SHA.fullmatch(result.get("sha") or ""):
            raise ValueError("native protected GitHub merge was not confirmed")
        native_merged = True
        merge_sha = result["sha"]
    except (ValueError, KeyError, TypeError, OSError,
            subprocess.CalledProcessError, subprocess.TimeoutExpired):
        if not native_merged:
            # Best effort revocation; a subsequent scheduled scan will also
            # clear any dangling green statuses after a runner interruption.
            for context in (SOURCE_STATUS, REVIEW_STATUS):
                try:
                    status(sha, context, "failure", "No completed authorized merge")
                except (OSError, ValueError):
                    pass
        raise
    print("TDQ_NATIVE_MERGED pr=%d head=%s merge=%s path=%s" %
          (number, sha, merge_sha, path), flush=True)
    try:
        merged = api("commits/" + merge_sha)
        if [p["sha"] for p in merged.get("parents", [])] != [old, sha]:
            raise MergedButUnverified("merge occurred but exact protected parentage is UNPROVEN")
        if api("git/ref/heads/main")["object"]["sha"] != merge_sha:
            raise MergedButUnverified("merge occurred but protected main moved unexpectedly")
        # GITHUB_TOKEN-driven merges may suppress normal Pages push builds.
        build = api("pages/builds", "POST")
        print("TDQ_PAGES_BUILD_REQUESTED " + str(build.get("status", "accepted")),
              flush=True)
        # The remote merge commit is NOT fetched into this Actions checkout.
        # We already verified protected parentage [old, candidate SHA]; the
        # candidate's immutable path blob is the published main result.
        expected = tdq.git("show", sha + ":" + path)
        url = "https://offbeatinc.com/" + path + "?tdq_verify=" + merge_sha[:12]
        for attempt in range(12):
            try:
                request = urllib.request.Request(
                    url, headers={"User-Agent": "TaskDatty-public-byte-verify/1",
                                  "Cache-Control": "no-cache"})
                with urllib.request.urlopen(request, timeout=12) as web:
                    actual = web.read(350_001)
                if actual == expected:
                    print("TDQ_PUBLIC_BYTES_VERIFIED path=" + path +
                          " merge=" + merge_sha, flush=True)
                    return
            except (OSError, ValueError) as ex:
                print("TDQ_PUBLIC_READBACK_RETRY " + type(ex).__name__, flush=True)
            time.sleep(15)
        raise MergedButUnverified("MERGED_BUT_LIVE_PAGE_BYTES_UNPROVEN: " + path)
    except (ValueError, OSError, KeyError,
            subprocess.CalledProcessError, subprocess.TimeoutExpired) as err:
        raise MergedButUnverified(
            "MERGED_BUT_POSTMERGE_EVIDENCE_UNPROVEN: " + type(err).__name__
        ) from err



def selftest_native_merge_and_publication():
    """No network/GitHub mutations: verify exact source/merge/readback control."""
    from unittest.mock import patch
    head, base, merged = "a"*40, "b"*40, "c"*40
    changes = []
    state = {"pages_fail": False}
    def fake_api(endpoint, method="GET", fields=None):
        changes.append((endpoint, method))
        if endpoint == "pulls/1":
            return {"draft": False}
        if endpoint == "pulls/1/merge":
            assert method == "PUT" and fields["sha"] == head
            return {"merged": True, "sha": merged}
        if endpoint == "commits/" + merged:
            return {"parents": [{"sha": base}, {"sha": head}]}
        if endpoint == "git/ref/heads/main":
            return {"object": {"sha": merged}}
        if endpoint == "pages/builds":
            if state["pages_fail"]:
                raise ValueError("mocked Pages build unavailable")
            return {"status": "queued"}
        raise AssertionError("unexpected protected API request: " + endpoint)
    class PublicBytes:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, limit):
            return b"TEST_PAGE_CONTENT"
    def fake_status(sha, name, status_name, reason):
        changes.append(("status", name, status_name))
    with patch.dict(globals(), {"check": lambda pr: (1, head, base, "guide.html"),
                                "policy_mode": lambda: "PROTECTED_RELEASE",
                                "verify_pages_source": lambda: None,
                                "api": fake_api, "status": fake_status,
                                "register_status_head": lambda pr, sha: None}), \
         patch.object(tdq, "git", return_value=b"TEST_PAGE_CONTENT"), \
         patch.object(urllib.request, "urlopen", return_value=PublicBytes()):
        finalize({"number": 1}, "PROTECTED_RELEASE")
        assert ("pulls/1/merge", "PUT") in changes
        assert ("pages/builds", "POST") in changes
        state["pages_fail"] = True
        try:
            finalize({"number": 1}, "PROTECTED_RELEASE")
        except MergedButUnverified:
            pass
        else:
            raise AssertionError("merged-but-unverified must FAIL CI rather than disappear")


def selftest():
    old = b'<!doctype html><main><p>Vague guidance.</p></main>'
    new = b'<!doctype html><main><p>Clearer guidance.</p></main>'
    low_risk_editorial(old, new, "guide.html")
    # True corrective rewrites may retain the already-present word "free"
    # while removing a false timeframe. A NEW claim/numeric price must fail.
    original = b'<!doctype html><main><p>Start with free software. You will mix within a week.</p></main>'
    corrected = b'<!doctype html><main><p>Start with free bundled software, practice regularly; no fixed timeline.</p></main>'
    low_risk_editorial(original, corrected, "beginner-dj-hub.html")
    try:
        low_risk_editorial(original,
            b'<!doctype html><main><p>Get free lifetime access for $500 today.</p></main>',
            "beginner-dj-hub.html")
    except ValueError:
        pass
    else:
        raise AssertionError("introduced price/promise must not pass gate")
    try:
        low_risk_editorial(
            b'<!doctype html><title>Original</title><main><p>Old.</p></main>',
            b'<!doctype html><title>Deceptive</title><main><p>Better.</p></main>',
            "guide.html")
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-main copy edit must not auto-release")
    try:
        low_risk_editorial(old, new, "contact.html")
    except ValueError:
        pass
    else:
        raise AssertionError("automated release must not change contact policy")
    try:
        low_risk_editorial(
            b'<!doctype html><main><p>Affiliate disclosure is required.</p></main>',
            b'<!doctype html><main><p>Useful introduction.</p></main>',
            "guide.html")
    except ValueError:
        pass
    else:
        raise AssertionError("removing required disclosure must be held")
    for bad in (b'<main><p>Clearer guidance.</p></main>',
                b'<!doctype html><main><div>Clearer guidance.</div></main>',
                b'<!doctype html><main><p>Guaranteed $100.</p></main>',
                b'<!doctype html><main><!-- changed --><p>Fine.</p></main>',
                b'<!doctype html><main><p>' + b"x" * 3500 + b'</p></main>'):
        try:
            low_risk_editorial(old, bad, "guide.html")
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe source modification was accepted")
    payload = {"schema":"tdq-review-v1","repo":REPO,"pr":1,
               "head":"a"*40,"base":"b"*40,"paths":["guide.html"],
               "verdict":"APPROVE","issued_at":123,"expires_at":456,
               "reviewer":"k11-isolated-ollama-review","reason":"Independent review verified this correction against policy."}
    assert not signed_review([], 1, "a"*40, "b"*40, "guide.html", 150)
    assert not signed_review([{"body":"<!-- TDQ-SIGNED-REVIEW-V1\n"+
                              json.dumps({"payload":payload,"signature":"junk"})+
                              "\n-->"}], 1, "a"*40, "b"*40, "guide.html", 150)
    # Exercise REAL Ed25519 signature verification using an ephemeral test
    # key, never the protected production reviewer private key.
    original_key = PUBLIC_KEY
    try:
        with tempfile.TemporaryDirectory(prefix="tdq-review-fixture-") as tmp:
            priv = Path(tmp, "reviewer.key")
            pub = Path(tmp, "reviewer.pub")
            source = Path(tmp, "payload")
            sig = Path(tmp, "signature")
            subprocess.run(["openssl", "genpkey", "-algorithm", "Ed25519",
                            "-out", str(priv)], check=True,
                           capture_output=True, timeout=15)
            subprocess.run(["openssl", "pkey", "-in", str(priv), "-pubout",
                            "-out", str(pub)], check=True,
                           capture_output=True, timeout=15)
            now = 100_000
            signed = dict(payload, issued_at=now, expires_at=now + 2000)
            source.write_bytes(canonical(signed))
            signature = subprocess.run(["openssl", "pkeyutl", "-sign",
                                        "-inkey", str(priv), "-rawin",
                                        "-in", str(source)], check=True,
                                       capture_output=True, timeout=15).stdout
            globals()["PUBLIC_KEY"] = pub
            encoded = base64.b64encode(signature).decode("ascii")
            assert verify_signature(signed, encoded)
            comment = lambda obj: [{"body":
                "<!-- TDQ-SIGNED-REVIEW-V1\n" +
                json.dumps({"payload": obj, "signature": encoded}) +
                "\n-->"}]
            # Real signed exact-head verification succeeds.
            assert signed_review(comment(signed), 1, "a"*40, "b"*40,
                                 "guide.html", now)
            assert not signed_review(comment(signed), 1, "c"*40, "b"*40,
                                     "guide.html", now)
            assert not signed_review(comment(signed), 1, "a"*40, "b"*40,
                                     "guide.html", now + 3000)
            # Later valid signed REJECT dominates earlier APPROVE.
            rejected = dict(signed, verdict="REJECT")
            # Rejection must carry a strictly newer signing time.
            rejected["issued_at"] = now + 1
            rejected["expires_at"] = now + 2001
            source.write_bytes(canonical(rejected))
            reject_sig = subprocess.run(["openssl", "pkeyutl", "-sign",
                                         "-inkey", str(priv), "-rawin",
                                         "-in", str(source)], check=True,
                                        capture_output=True, timeout=15).stdout
            reject_entry = {"body": "<!-- TDQ-SIGNED-REVIEW-V1\n" +
                json.dumps({"payload": rejected,
                            "signature": base64.b64encode(reject_sig).decode()}) +
                "\n-->"}
            assert not signed_review(comment(signed)+[reject_entry], 1,
                                     "a"*40, "b"*40, "guide.html", now)
            # A later posted replay of the old APPROVE cannot defeat REJECT.
            assert not signed_review(comment(signed)+[reject_entry]+comment(signed),
                                     1, "a"*40, "b"*40, "guide.html", now)
            # Even after the later REJECT expires, the older approval cannot
            # revive just because it has an unexpired envelope.
            short_reject = dict(rejected, expires_at=now+2)
            source.write_bytes(canonical(short_reject))
            short_sig = subprocess.run(
                ["openssl", "pkeyutl", "-sign", "-inkey", str(priv),
                 "-rawin", "-in", str(source)],
                check=True, capture_output=True, timeout=15).stdout
            short_entry = {"body": "<!-- TDQ-SIGNED-REVIEW-V1\n"
                + json.dumps({"payload": short_reject,
                 "signature": base64.b64encode(short_sig).decode()}) + "\n-->"}
            assert not signed_review(comment(signed)+[short_entry], 1,
                                     "a"*40, "b"*40, "guide.html", now+3)
    finally:
        globals()["PUBLIC_KEY"] = original_key
    # The append-only GitHub Actions ledger is written BEFORE any green
    # status; a closed/renamed PR still retains its immutable logged SHA.
    ledgertime = []
    prev_api = globals()["api"]
    try:
        def ledger_fixture(endpoint, method="GET", fields=None):
            ledgertime.append((endpoint, method))
            if endpoint.startswith("issues/838/comments?"):
                return [{"user": {"login": "attacker"},
                         "body": "TDQ_GREEN_V1 pr=2 head=" + "z"*40},
                        {"user": {"login": "github-actions[bot]"},
                         "body": "TDQ_GREEN_V1 pr=3 head=" + "c"*40}]
            if endpoint == "issues/838/comments" and method == "POST":
                assert fields == {"body": "TDQ_GREEN_V1 pr=1 head=" + "a"*40}
                return {"id": 100}
            raise AssertionError("unexpected ledger endpoint: " + endpoint)
        globals()["api"] = ledger_fixture
        assert ledger_issued_heads() == {"c"*40}
        register_status_head(1, "a"*40)
        assert ledgertime[-1] == ("issues/838/comments", "POST")
    finally:
        globals()["api"] = prev_api
    # The existing incompatible DatBotty rules may permit status-only
    # preflight, but no native merge. A mocked GitHub config exercises
    # exact integration IDs, active main scope and no bypass authority.
    legacy = {
        "enforcement": "active", "target": "branch", "source": REPO,
        "conditions": {"ref_name": {"include": ["refs/heads/main"],
                                     "exclude": []}},
        "bypass_actors": [{"actor_type": "User", "actor_id": 191937709}],
        "current_user_can_bypass": "pull_requests_only",
        "rules": [
            {"type": "pull_request", "parameters": {
                "required_review_thread_resolution": True,
                "dismiss_stale_reviews_on_push": True}},
            {"type": "required_status_checks", "parameters": {
                "strict_required_status_checks_policy": True,
                "required_status_checks": [
                    {"context": "DatBotty Deterministic Gate",
                     "integration_id": 15368},
                    {"context": "DatBotty T1 Review",
                     "integration_id": 15368}]}}]}
    orig_api = globals()["api"]
    try:
        globals()["api"] = lambda path: legacy
        assert policy_mode() == "PREFLIGHT_ONLY"
        new_rules = json.loads(json.dumps(legacy))
        new_rules["bypass_actors"] = []
        new_rules["current_user_can_bypass"] = "never"
        new_rules["rules"][1]["parameters"]["required_status_checks"] = [
            {"context": SOURCE_STATUS, "integration_id": 15368},
            {"context": REVIEW_STATUS, "integration_id": 15368}]
        globals()["api"] = lambda path: new_rules
        assert policy_mode() == "PROTECTED_RELEASE"
        no_actor_info = json.loads(json.dumps(new_rules))
        del no_actor_info["bypass_actors"]
        globals()["api"] = lambda path: no_actor_info
        assert policy_mode() == "PROTECTED_RELEASE", (
            "missing admin list must not prevent a non-bypass Actions actor")
        for unsafe in ("excluded", "status", "executor-bypass"):
            bad = json.loads(json.dumps(new_rules))
            if unsafe == "excluded":
                bad["conditions"]["ref_name"]["exclude"] = ["refs/heads/*"]
            elif unsafe == "executor-bypass":
                bad["current_user_can_bypass"] = "pull_requests_only"
            else:
                bad["rules"][1]["parameters"]["required_status_checks"][1][
                    "integration_id"] = 0
            globals()["api"] = lambda path, data=bad: data
            try:
                policy_mode()
            except ValueError:
                pass
            else:
                raise AssertionError("unsafe native ruleset accepted: " + unsafe)
    finally:
        globals()["api"] = orig_api
    # A green GitHub status is durable; verify crashed-run cleanup and the
    # preflight success->pending transition so legacy gate proof cannot leave
    # a reusable old approval on an open PR.
    old_api, old_status = globals()["api"], globals()["status"]
    old_ledger = globals()["ledger_issued_heads"]
    old_register = globals()["register_status_head"]
    old_check = globals()["check"]
    old_pages = globals()["verify_pages_source"]
    old_policy = globals()["policy_mode"]
    try:
        captured = []
        globals()["api"] = lambda endpoint: {"statuses": [
            {"context": SOURCE_STATUS, "state": "success"},
            {"context": REVIEW_STATUS, "state": "pending"}]}
        globals()["status"] = lambda sha, name, state, msg: captured.append(
            (sha, name, state))
        globals()["register_status_head"] = lambda pr, sha: None
        sample = {"state": "open", "head": {
            "sha": "a"*40, "ref": "tdq/proof-auto-1234567890abcd",
            "repo": {"full_name": REPO}}}
        globals()["ledger_issued_heads"] = lambda: {"a"*40}
        revoke_ledger_statuses()
        assert captured == [("a"*40, SOURCE_STATUS, "pending")]
        captured.clear()
        globals()["check"] = lambda pr: (1, "a"*40, "b"*40, "guide.html")
        globals()["verify_pages_source"] = lambda: None
        globals()["policy_mode"] = lambda: "PREFLIGHT_ONLY"
        finalize(sample, "PREFLIGHT_ONLY")
        assert captured == [
            ("a"*40, SOURCE_STATUS, "success"),
            ("a"*40, REVIEW_STATUS, "success"),
            ("a"*40, SOURCE_STATUS, "pending"),
            ("a"*40, REVIEW_STATUS, "pending")]
    finally:
        globals()["api"] = old_api
        globals()["status"] = old_status
        globals()["check"] = old_check
        globals()["verify_pages_source"] = old_pages
        globals()["policy_mode"] = old_policy
        globals()["ledger_issued_heads"] = old_ledger
        globals()["register_status_head"] = old_register
    selftest_native_merge_and_publication()
    print("TDQ_SIGNED_GATE_SELFTEST_OK")


def ledger_issued_heads():
    """Durable trusted GitHub Actions ledger of EVERY success-issued SHA.

    A PR may have been closed, renamed, rewritten or rebased since the status
    was issued. Therefore neither current open PRs nor current head refs can
    reliably enumerate candidates needing a status revocation.
    """
    issued = set()
    for page in range(1, 41):
        comments = api("issues/%d/comments?per_page=100&page=%d" %
                       (STATUS_LEDGER_ISSUE, page))
        if not isinstance(comments, list):
            raise ValueError("protected status ledger unreadable")
        for comment in comments:
            author = (comment.get("user") or {}).get("login")
            if author != "github-actions[bot]":
                continue
            record = STATUS_LEDGER_ENTRY.fullmatch(
                (comment.get("body") or "").strip())
            if record:
                issued.add(record.group(2))
        if len(comments) < 100:
            return issued
    # Never pretend all green SHAs were swept after truncated pagination.
    raise ValueError("protected status ledger exceeded bounded pagination")


def register_status_head(pr, sha):
    if not SHA.fullmatch(sha) or not isinstance(pr, int) or pr < 1:
        raise ValueError("invalid SHA or PR for protected status ledger")
    if sha not in ledger_issued_heads():
        api("issues/%d/comments" % STATUS_LEDGER_ISSUE, "POST", {
            "body": "TDQ_GREEN_V1 pr=%d head=%s" % (pr, sha)})
    # A failed write means statuses MUST NOT be issued. A later scheduled scan
    # always has this durable SHA even if run is killed between green+merge.


def revoke_ledger_statuses():
    """Invalidate every old success SHA, regardless of PR state or ref name."""
    for sha in sorted(ledger_issued_heads()):
        combined = api("commits/" + sha + "/status?per_page=100")
        statuses = combined.get("statuses") or []
        if not isinstance(statuses, list) or len(statuses) >= 100:
            raise ValueError("protected status history unbounded")
        states = {}
        # API orders statuses newest-first; reverse to choose last context
        # state. Ignore other repositories' standard GitHub status contexts.
        for item in reversed(statuses):
            if item.get("context") in (SOURCE_STATUS, REVIEW_STATUS):
                states[item["context"]] = item.get("state")
        for context in (SOURCE_STATUS, REVIEW_STATUS):
            if states.get(context) == "success":
                status(sha, context, "pending",
                       "Expired/withdrawn signed review status requires new gate")
                print("TDQ_LEDGER_STATUS_INVALIDATED sha=" + sha[:12] +
                      " context=" + context, flush=True)


def main():
    if "--self-test" in sys.argv:
        selftest()
        return
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise ValueError("wrong repository; no release authority")
    if not all(os.environ.get(x) for x in ("GH_TOKEN", "GITHUB_RUN_ID",
                                           "GITHUB_SERVER_URL")):
        raise ValueError("missing trusted workflow identity")
    selftest()
    mode = policy_mode()  # Legacy remains protected, preflight only.
    prs = api("pulls?state=open&per_page=100")
    if len(prs) >= 100:
        raise ValueError("unbounded PR inventory")
    revoke_ledger_statuses()
    for pr in sorted(prs, key=lambda x: x["number"]):
        if (not (pr.get("head") or {}).get("ref", "").startswith("tdq/proof-auto-")
                or RELEASE not in {x.get("name") for x in pr.get("labels", [])}
                or HOLD in {x.get("name") for x in pr.get("labels", [])}):
            continue
        try:
            finalize(pr, mode)
            return
        except (ValueError, KeyError, TypeError, OSError,
                subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print("TDQ_RELEASE_WITHHELD pr=%s reason=%s" %
                  (pr.get("number"), str(e)[:140]), file=sys.stderr)
    print("TDQ_NO_VERIFIED_RELEASE_AVAILABLE")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, MergedButUnverified,
            subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print("TDQ_PROTECTED_ABORTED " + str(error)[:140], file=sys.stderr)
        sys.exit(2)
