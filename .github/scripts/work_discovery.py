"""Closed, deterministic renewable work contract shared by execution and provider.

No target code is executed. Only literal Git blobs under reviewed #658 paths
are parsed. The model never chooses a detector, scope, fingerprint or profile.
"""
from __future__ import annotations

import hashlib
import json
import math
import posixpath
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

VERSION = 1
MAX_FINDINGS = 4096
MAX_FILE_BYTES = 1024 * 1024
MAX_SCAN_SECONDS = 60
# Small initial registry; additional classes require source review. No arbitrary
# editorial/commerce detector or caller-provided allowlist exists.
DETECTORS = {
    'missing-description-v1': ('offbeat-658-pkg-2', 'offbeat_content_batch', (
        'best-dj-controllers-2026.html', 'best-dj-controllers-under-200.html',
        'best-dj-controllers-under-300.html', 'best-dj-controllers-under-500-2026.html',
        'best-dj-controllers-under-1000.html', 'dj-controllers-hub.html')),
    'broken-internal-link-v1': ('offbeat-658-pkg-3', 'offbeat_content_batch', (
        'best-dj-software.html', 'best-dj-software-beginners-2026.html',
        'best-free-dj-software-2026.html', 'dj-software-hub.html',
        'rekordbox-vs-serato.html', 'serato-vs-rekordbox-vs-traktor.html', 'virtual-dj-vs-serato.html')),
    'missing-image-alt-v1': ('offbeat-658-pkg-5', 'offbeat_accessibility_batch', (
        'index.html', 'about.html', 'contact.html', 'disclosure.html', 'privacy.html', '404.html')),
    'invalid-jsonld-v1': ('offbeat-658-pkg-6', 'offbeat_structured_data_batch', (
        'index.html','all-dj-guides.html','beginner-dj-hub.html','dj-controllers-hub.html',
        'dj-software-hub.html','dj-gear-hub.html','dj-skills-performance-hub.html')),
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def git(repo, *args):
    result = subprocess.run(['git','--no-replace-objects','-c','core.hooksPath=/dev/null',*args],
        cwd=repo,capture_output=True,timeout=10,check=True)
    if len(result.stdout)>MAX_FILE_BYTES:
        raise RuntimeError('discovery Git output exceeds bound')
    return result.stdout


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags=[]
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag,dict(attrs)))


def findings(detector, path, text, inventory):
    tags=Page(text).tags
    if detector=='missing-description-v1':
        if not any(t=='meta' and a.get('name','').lower()=='description' and str(a.get('content') or '').strip() for t,a in tags):
            return [{'missing':'meta[name=description]'}]
    elif detector=='missing-image-alt-v1':
        return sorted(({'src':a.get('src') or '', 'missing':'alt'} for t,a in tags if t=='img' and 'alt' not in a),key=canonical)
    elif detector=='broken-internal-link-v1':
        broken=[]
        for tag,attrs in tags:
            href=attrs.get('href') or ''
            if tag!='a' or not href or href.startswith('#'): continue
            parsed=urlsplit(href)
            if parsed.scheme or parsed.netloc: continue
            target=unquote(parsed.path)
            target=posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join(posixpath.dirname(path),target))
            if target in ('','.') or parsed.path.endswith('/'): target=target.rstrip('/')+'/index.html' if target not in ('','.') else 'index.html'
            if target.startswith('../') or target not in inventory:
                broken.append({'href':href,'missing_target':target})
        return sorted(broken,key=canonical)
    elif detector=='invalid-jsonld-v1':
        failures=[]
        for raw in re.findall(r'''<script\b[^>]*type=["']application/ld\+json["'][^>]*>(.*?)</script>''',text,re.I|re.S):
            try: json.loads(raw,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
            except ValueError: failures.append({'invalid_jsonld_sha256':hashlib.sha256(raw.encode()).hexdigest()})
        return sorted(failures,key=canonical)
    return []


def objective_satisfied(item, before, after, inventory):
    """A renamed defect is not a repair: require strict reduction, no new debt."""
    from collections import Counter
    args=(item['detector_id'],item['target_files'][0])
    old=Counter(canonical(v) for v in findings(*args,before,inventory))
    new=Counter(canonical(v) for v in findings(*args,after,inventory))
    return (canonical(item['evidence']) not in new and sum(new.values())<sum(old.values())
            and not (new-old))


def discover(repo, base_sha, discovered_at):
    import time
    if not isinstance(base_sha,str) or not re.fullmatch('[0-9a-f]{40}',base_sha):
        raise RuntimeError('discovery requires exact base SHA')
    if type(discovered_at) not in (float,int) or not math.isfinite(discovered_at) or discovered_at<=0:
        raise RuntimeError('invalid discovery timestamp')
    deadline=time.monotonic()+MAX_SCAN_SECONDS
    inventory=set(git(repo,'ls-tree','-r','--name-only',base_sha).decode().splitlines())
    result=[]; seen=set()
    for detector,(package,profile,paths) in DETECTORS.items():
        for path in paths:
            if time.monotonic()>=deadline: raise RuntimeError('discovery wall deadline exceeded')
            if path not in inventory: continue
            mode=git(repo,'ls-tree',base_sha,'--',path).decode()
            if not mode.startswith('100644 blob '): raise RuntimeError('discovery target is not regular data')
            body=git(repo,'show',f'{base_sha}:{path}')
            last_change=git(repo,'log','-1','--format=%H',base_sha,'--',path).decode().strip()
            for evidence in findings(detector,path,body.decode('utf-8'),inventory):
                fingerprint=digest({'detector':detector,'path':path,'evidence':evidence})
                if fingerprint in seen: continue
                seen.add(fingerprint)
                material=dict(schema_version=VERSION,detector_id=detector,detector_version=1,
                    package_id=package,verification_profile=profile,base_sha=base_sha,
                    fingerprint=fingerprint,evidence=evidence,target_files=[path],
                    source_body_sha256=hashlib.sha256(body).hexdigest(),last_change_sha=last_change,
                    dependencies={'inventory_sha256':digest(sorted(inventory))})
                result.append(material|{'work_item_id':digest(material),'discovered_at':discovered_at})
                if len(result)>MAX_FINDINGS: raise RuntimeError('discovery finding bound exceeded; never report a truncated backlog')
    return result


def validate_work_item(repo, item, base_sha, candidate_sha=None):
    if not isinstance(item,dict) or item.get('base_sha')!=base_sha:
        raise RuntimeError('work item base mismatch')
    # Exact recomputation rejects model-authored evidence/category/scope expansion.
    matches=[v for v in discover(repo,base_sha,item.get('discovered_at')) if v['work_item_id']==item.get('work_item_id')]
    if len(matches)!=1 or matches[0]!=item:
        raise RuntimeError('untrusted or stale deterministic work item')
    if candidate_sha is not None:
        changed=git(repo,'diff','--name-only',base_sha,candidate_sha).decode().splitlines()
        if not changed or not set(changed)<=set(item['target_files']):
            raise RuntimeError('candidate exceeds finding target scope')
        inventory=set(git(repo,'ls-tree','-r','--name-only',candidate_sha).decode().splitlines())
        path=item['target_files'][0]
        after=git(repo,'show',f'{candidate_sha}:{path}').decode('utf-8')
        before=git(repo,'show',f'{base_sha}:{path}').decode('utf-8')
        if not objective_satisfied(item,before,after,inventory):
            raise RuntimeError('discovered defect remains in candidate')
    return item
