#!/usr/bin/env python3
"""Offline structural checks. This cannot establish source truth or aesthetic quality."""
import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

SECTIONS = ("身份与作品事实", "创作阶段与适用范围", "有来源的理念", "应用性评片规则", "成立条件与反例", "建议与练习", "来源与研究边界")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
CLAIM = re.compile(r"^\s*[-*]?\s*\*\*([FIR]\d+)\*\*", re.M)
PLACEHOLDER = re.compile(r"(?im)^\s*(?:[-*]\s*)?(?:TODO|TBD|FIXME|INSERT HERE|\[待填写\])\b")

def validate(root):
    root = root.resolve()
    errors = []

    def error(message):
        errors.append(message)

    def inside(relative, base=None):
        if not isinstance(relative, str) or not relative:
            error("invalid file path")
            return None
        path = ((base or root) / relative).resolve()
        if not path.is_relative_to(root):
            error(f"outside package: {relative}")
            return None
        if not path.is_file():
            error(f"missing file: {path.relative_to(root)}")
            return None
        return path

    def read_json(relative):
        path = inside(relative)
        if path is None:
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            error(f"invalid JSON: {relative}: {exc}")
            return None

    def markdown(path):
        try:
            body = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            error(f"cannot read {path}: {exc}")
            return ""
        if PLACEHOLDER.search(body):
            error(f"unfinished placeholder: {path.name}")
        # Code blocks are explanatory text, not live Markdown links.
        stripped = re.sub(r"```.*?```", "", body, flags=re.S)
        stripped = re.sub(r"(`+).*?\1", "", stripped)
        links = LINK.findall(stripped)
        links += re.findall(r"^\s{0,3}\[([^\]]+)\]:\s*(<[^>]+>|\S+)", stripped, flags=re.M)
        for _, href in links:
            href = href.strip("<>")
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            relative = unquote(href.split("#", 1)[0])
            if relative:
                inside(relative, path.parent)
        return body

    entry = inside("SKILL.md")
    if entry:
        body = markdown(entry)
        match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", body, re.S)
        if not match or not re.search(r"^name:\s*photo-critique-panel\s*$", match[1], re.M) or not re.search(r"^description:\s*\S", match[1], re.M):
            error("invalid skill frontmatter (name/description)")
    ui = inside("agents/openai.yaml")
    if ui:
        try:
            ui_text = ui.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            error(f"cannot read UI metadata: {exc}")
            ui_text = ""
        group = None
        fields = {}
        allowed_groups = {"interface", "policy"}
        for line in ui_text.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if re.fullmatch(r"[a-z_]+:", line):
                group = line[:-1]
                if group not in allowed_groups:
                    error(f"unsupported UI group: {group}")
                continue
            match = re.fullmatch(r'  ([a-z_]+): (".*"|true|false)', line)
            if not match or group not in allowed_groups:
                error("invalid UI YAML (use documented quoted scalar format)")
                continue
            try:
                value = json.loads(match[2])
            except json.JSONDecodeError:
                error("invalid UI quoted value")
                continue
            key = (group, match[1])
            if key in fields:
                error("duplicate UI field")
            fields[key] = value
        for name in ("display_name", "short_description", "default_prompt"):
            if not isinstance(fields.get(("interface", name)), str) or not fields[("interface", name)].strip():
                error(f"UI missing string field: {name}")
        if not 25 <= len(str(fields.get(("interface", "short_description"), ""))) <= 64:
            error("UI short_description must be 25–64 characters")
        if "$photo-critique-panel" not in str(fields.get(("interface", "default_prompt"), "")):
            error("UI default prompt lacks skill invocation")

    registry = read_json("references/registry.json")
    if not isinstance(registry, dict) or not isinstance(registry.get("judges"), list):
        error("registry must contain a judges array")
        return errors
    judges = registry["judges"]
    if registry.get("schema_version") != 1:
        error("unknown registry schema version")
    if len(judges) != 22:
        error(f"expected 22 judges, got {len(judges)}")
    valid_judges = [j for j in judges if isinstance(j, dict)]
    if len(valid_judges) != len(judges):
        error("judge record must be an object")
    well_formed = []
    for j in valid_judges:
        if not all(isinstance(j.get(k), str) and j[k].strip() for k in ("id", "role", "name", "name_ja", "profile", "source_file")):
            error("invalid judge fields (expected non-empty strings)")
            continue
        well_formed.append(j)
    valid_judges = well_formed
    counts = Counter(j.get("role") for j in valid_judges)
    if counts != Counter(photographer=10, critic=2, professor=10):
        error(f"invalid role counts: {dict(counts)}")
    ids = [j.get("id") for j in valid_judges]
    if len(set(ids)) != len(ids):
        error("duplicate judge id")
    for j in valid_judges:
        if not isinstance(j.get("id"), str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", j["id"]):
            error("invalid judge id")
        if not all(isinstance(j.get(k), str) and j[k].strip() for k in ("name", "name_ja", "profile", "source_file")):
            error(f"incomplete judge record: {j.get('id')}")

    source_records = []
    for filename in sorted(set(j.get("source_file", "") for j in valid_judges)):
        records = read_json(filename)
        if not isinstance(records, list):
            error(f"source file must be an array: {filename}")
            continue
        for s in records:
            if isinstance(s, dict):
                source_records.append(s)
            else:
                error("source record must be an object")
    well_formed_sources = []
    for s in source_records:
        if not all(isinstance(s.get(k), str) and s[k].strip() for k in ("id", "person_id", "title", "author", "publisher", "url", "locator", "read_scope", "kind")):
            error("invalid source fields (expected non-empty strings)")
            continue
        well_formed_sources.append(s)
    source_records = well_formed_sources
    source_ids = [s.get("id") for s in source_records]
    if len(set(source_ids)) != len(source_ids):
        error("duplicate source id")
    sources_by_person = {ident: [] for ident in ids}
    for s in source_records:
        sid = s.get("id", "unknown")
        for field in ("id", "person_id", "title", "author", "publisher", "url", "locator", "read_scope", "kind"):
            if not isinstance(s.get(field), str) or not s[field].strip():
                error(f"missing source field {field}: {sid}")
        try:
            parsed = urlsplit(s["url"])
        except ValueError:
            parsed = None
        if parsed is None or parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
            error(f"invalid source URL: {sid}")
        for field in ("published", "accessed"):
            value = s.get(field)
            if value is None and field == "published":
                continue
            try:
                date.fromisoformat(value)
            except (ValueError, TypeError):
                error(f"invalid source date ({field}): {sid}")
        if not isinstance(s.get("substantive"), bool):
            error(f"substantive must be boolean: {sid}")
        if s.get("substantive") and re.search(r"excerpt|snippet|仅搜索|检索摘要", str(s.get("read_scope", "")), re.I):
            error(f"excerpt cannot be substantive: {sid}")
        if s.get("substantive") and s.get("kind") in ("bibliography", "faculty_listing", "research_record"):
            error(f"listing/bibliography is not substantive: {sid}")
        if not isinstance(s.get("supports"), list) or not all(isinstance(c, str) for c in s["supports"]):
            error(f"supports must be a claim array: {sid}")
        if s.get("substantive") and not s.get("supports"):
            error(f"substantive source lacks supported claims: {sid}")
        visual = s.get("visual_inspection")
        if not isinstance(visual, dict) or visual.get("status") not in ("not_viewed", "viewed") or not isinstance(visual.get("detail"), str) or not visual["detail"]:
            error(f"invalid visual inspection record: {sid}")
        person = s.get("person_id")
        if person not in sources_by_person:
            error(f"unknown source person: {sid}")
        else:
            sources_by_person[person].append(s)

    for j in valid_judges:
        person = j.get("id")
        sources = sources_by_person.get(person, [])
        substantive = {s.get("url") for s in sources if s.get("substantive")}
        if len(substantive) < 2:
            error(f"need two distinct substantive materials: {person}")
        if j.get("role") == "professor" and not any(s.get("kind") in ("faculty_listing", "faculty_profile") for s in sources):
            error(f"professor lacks faculty record: {person}")
        path = inside(j.get("profile", ""))
        if path is None:
            continue
        body = markdown(path)
        for section in SECTIONS:
            if f"## {section}" not in body:
                error(f"missing profile section {section}: {person}")
        claims = CLAIM.findall(body)
        if len(set(claims)) != len(claims):
            error(f"duplicate claim: {person}")
        if any(not any(c.startswith(prefix) for c in claims) for prefix in "FIR"):
            error(f"profile needs fact, idea, inference: {person}")
        local = {s.get("id"): s for s in sources}
        for label, url in LINK.findall(body):
            if label in local and url != local[label].get("url"):
                error(f"citation URL differs from metadata: {person}/{label}")
            elif re.match(r"[ptc]-", label) and label not in local:
                error(f"unknown citation source: {person}/{label}")
        for s in sources:
            for claim in s.get("supports", []) if isinstance(s.get("supports"), list) else []:
                if claim not in claims:
                    error(f"unknown claim {person}/{claim} in source {s.get('id')}")
        for claim in claims:
            segment = re.split(r"^\s*[-*]?\s*\*\*[FIR]\d+\*\*|^## ", body.split(f"**{claim}**", 1)[1], maxsplit=1, flags=re.M)[0]
            refs = [label for label, _ in LINK.findall(segment) if label in local]
            if not refs:
                error(f"claim lacks registered citation: {person}/{claim}")
            if claim.startswith(("F", "I")) and not any(claim in local[label].get("supports", []) for label in refs):
                error(f"cited claim not mapped to source supports: {person}/{claim}")
            if claim.startswith("R"):
                ideas = re.findall(r"(?<![A-Za-z0-9])I\d+(?![A-Za-z0-9])", segment)
                if not ideas:
                    error(f"inference lacks idea mapping: {person}/{claim}")
                for idea in ideas:
                    if idea not in claims:
                        error(f"inference maps to unknown idea: {person}/{claim}/{idea}")
                for label in refs:
                    if not any(idea in local[label].get("supports", []) for idea in ideas):
                        error(f"inference source does not support its idea: {person}/{claim}/{label}")

    # Also validate portable links in shared references and repository documentation.
    for path in root.rglob("*.md"):
        if any(part in (".git", "__pycache__") for part in path.relative_to(root).parts):
            continue
        if path == entry or path.parent.name == "judges":
            continue
        markdown(path)
    return errors

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate(args.root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAILED: {len(errors)} structural errors")
        return 1
    print("PASS: 22 profiles, 10/2/10 roles, sources, claims and portable links validated.")
    print("This is structural validation, not source-truth or model-behavior verification.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
