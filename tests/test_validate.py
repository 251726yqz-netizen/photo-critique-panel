"""Exercise broken-package behavior, not a particular generated prose style."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

VALIDATOR = Path(__file__).parents[1] / "scripts" / "validate.py"
SECTIONS = ["身份与作品事实", "创作阶段与适用范围", "有来源的理念", "应用性评片规则", "成立条件与反例", "建议与练习", "来源与研究边界"]

class PackageValidation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "references/judges").mkdir(parents=True)
        (self.root / "references/sources").mkdir()
        (self.root / "agents").mkdir()
        (self.root / "SKILL.md").write_text('---\nname: photo-critique-panel\ndescription: Use when evaluating photography.\n---\nSee [roster](references/registry.json).\n', encoding="utf-8")
        (self.root / "agents/openai.yaml").write_text('interface:\n  display_name: "写真评片"\n  short_description: "独立评价照片、组照、作品集和本科及修士申请材料，提供有来源的评片依据"\n  default_prompt: "Use $photo-critique-panel."\n', encoding="utf-8")
        self.registry = {"schema_version": 1, "skill_version": "0.1.0", "judges": []}
        self.sources = []
        for n in range(22):
            ident = f"judge-{n:02}"
            role = "photographer" if n < 10 else "critic" if n < 12 else "professor"
            self.registry["judges"].append({"id": ident, "name": f"人物{n}", "name_ja": f"人物{n}", "role": role, "profile": f"references/judges/{ident}.md", "source_file": "references/sources/test.json"})
            links = []
            for k in range(2):
                sid = f"{ident}-s{k}"
                url = f"https://university.example/{ident}/{k}"
                links.append(f"[{sid}]({url})")
                self.sources.append({"id":sid, "person_id":ident, "title":"A substantive teaching statement", "author":"University", "publisher":"University", "url":url, "published":None, "accessed":"2026-10-14", "locator":"Teaching statement paragraphs 1-3", "read_scope":"Relevant paragraphs read", "kind":"faculty_profile" if role == "professor" else "interview", "substantive":True, "supports":["F1","I1"], "visual_inspection":{"status":"not_viewed", "detail":"Text-only test record"}, "notes":"Synthetic metadata for validator testing"})
            md = f"# {ident}\n\n## {SECTIONS[0]}\n- **F1** Fact. {links[0]}\n\n## {SECTIONS[1]}\nSpecific phase.\n\n## {SECTIONS[2]}\n- **I1** Idea. {' '.join(links)}\n\n## {SECTIONS[3]}\n- **R1** Inference based on I1. {links[1]}\n"
            md += "".join(f"\n## {s}\nA meaningful boundary or exercise.\n" for s in SECTIONS[4:])
            (self.root / f"references/judges/{ident}.md").write_text(md, encoding="utf-8")
        self.save()

    def save(self):
        (self.root / "references/registry.json").write_text(json.dumps(self.registry, ensure_ascii=False), encoding="utf-8")
        (self.root / "references/sources/test.json").write_text(json.dumps(self.sources, ensure_ascii=False), encoding="utf-8")

    def run_validator(self):
        self.save()
        return subprocess.run([sys.executable, str(VALIDATOR), "--root", str(self.root)], text=True, capture_output=True)

    def assert_rejected(self, marker):
        result = self.run_validator()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(marker, result.stdout + result.stderr)

    def test_accepts_complete_portable_package(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("22", result.stdout)

    def test_duplicate_judge_is_rejected(self):
        self.registry["judges"][1]["id"] = self.registry["judges"][0]["id"]
        self.assert_rejected("duplicate judge")

    def test_missing_profile_is_rejected(self):
        (self.root / self.registry["judges"][0]["profile"]).unlink()
        self.assert_rejected("missing file")

    def test_path_cannot_escape_package(self):
        self.registry["judges"][0]["profile"] = "../outside.md"
        self.assert_rejected("outside package")

    def test_duplicate_material_does_not_count_twice(self):
        self.sources[1]["url"] = self.sources[0]["url"]
        self.assert_rejected("two distinct substantive")

    def test_excerpt_alone_is_not_substantive(self):
        self.sources[0]["read_scope"] = "search excerpt only"
        self.assert_rejected("excerpt")

    def test_source_cannot_support_absent_claim(self):
        self.sources[0]["supports"].append("I999")
        self.assert_rejected("unknown claim")

    def test_source_id_cannot_be_reused(self):
        self.sources[1]["id"] = self.sources[0]["id"]
        self.assert_rejected("duplicate source")

    def test_professor_needs_official_faculty_record(self):
        for source in self.sources:
            if source["person_id"] == "judge-12":
                source["kind"] = "interview"
        self.assert_rejected("faculty record")

    def test_citation_url_must_match_record(self):
        path = self.root / self.registry["judges"][0]["profile"]
        path.write_text(path.read_text().replace("https://university.example/judge-00/0", "https://different.example/"), encoding="utf-8")
        self.assert_rejected("citation URL")

    def test_unfinished_profile_is_rejected(self):
        path = self.root / self.registry["judges"][0]["profile"]
        path.write_text(path.read_text() + "\nTODO: insert source\n", encoding="utf-8")
        self.assert_rejected("placeholder")

    def test_broken_local_reference_is_rejected(self):
        path = self.root / "SKILL.md"
        path.write_text(path.read_text() + "\n[missing](references/absent.md)\n", encoding="utf-8")
        self.assert_rejected("missing file")

    def test_malformed_json_is_reported_without_traceback(self):
        self.save()
        (self.root / "references/registry.json").write_text("{", encoding="utf-8")
        result = subprocess.run([sys.executable, str(VALIDATOR), "--root", str(self.root)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid JSON", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_impossible_date_is_rejected(self):
        self.sources[0]["accessed"] = "2026-99-99"
        self.assert_rejected("date")

    def test_chinese_inference_mapping_is_recognized(self):
        path = self.root / self.registry["judges"][0]["profile"]
        path.write_text(path.read_text().replace("Inference based on I1.", "由I1推导：检查可见事实。"), encoding="utf-8")
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_inference_cannot_map_to_absent_idea(self):
        path = self.root / self.registry["judges"][0]["profile"]
        path.write_text(path.read_text().replace("based on I1", "based on I999"), encoding="utf-8")
        self.assert_rejected("unknown idea")

    def test_cited_idea_needs_reverse_source_mapping(self):
        for source in self.sources:
            if source["person_id"] == "judge-00":
                source["supports"].remove("I1")
        self.assert_rejected("not mapped")

    def test_inference_source_must_support_its_idea(self):
        self.sources[0]["supports"] = ["F1"]
        path = self.root / self.registry["judges"][0]["profile"]
        body = path.read_text().replace("Inference based on I1. [judge-00-s1](https://university.example/judge-00/1)", "Inference based on I1. [judge-00-s0](https://university.example/judge-00/0)")
        path.write_text(body, encoding="utf-8")
        self.assert_rejected("inference source")

    def test_bibliography_cannot_count_as_substantive(self):
        self.sources[0]["kind"] = "bibliography"
        self.assert_rejected("not substantive")

    def test_invalid_ui_yaml_is_rejected(self):
        (self.root / "agents/openai.yaml").write_text("# $photo-critique-panel\ninterface: [\n", encoding="utf-8")
        self.assert_rejected("UI")

    def test_invalid_ui_encoding_is_reported_without_traceback(self):
        (self.root / "agents/openai.yaml").write_bytes(b"\xff\xfe")
        result = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot read UI", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_broken_image_link_is_rejected(self):
        path = self.root / "SKILL.md"
        path.write_text(path.read_text() + "\n![preview](missing.png)\n", encoding="utf-8")
        self.assert_rejected("missing file")

    def test_broken_reference_link_in_docs_is_rejected(self):
        (self.root / "docs").mkdir()
        (self.root / "docs/report.md").write_text("Read [document][doc].\n\n[doc]: ../missing.md\n", encoding="utf-8")
        self.assert_rejected("missing file")

    def test_link_example_inside_inline_code_is_literal(self):
        path = self.root / "SKILL.md"
        path.write_text(path.read_text() + "\nExample syntax: `![preview](missing.png)`\n", encoding="utf-8")
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_malformed_fields_return_errors_not_tracebacks(self):
        mutations = [
            ("judge", "role", {}), ("judge", "id", []),
            ("judge", "source_file", None), ("source", "id", []),
            ("source", "person_id", []), ("source", "url", "https://["),
        ]
        for target, field, value in mutations:
            with self.subTest(target=target, field=field):
                old = copy.deepcopy(self.registry if target == "judge" else self.sources)
                (self.registry["judges"][0] if target == "judge" else self.sources[0])[field] = value
                result = self.run_validator()
                self.assertEqual(result.returncode, 1)
                self.assertIn("ERROR", result.stdout)
                self.assertNotIn("Traceback", result.stderr)
                if target == "judge":
                    self.registry = old
                else:
                    self.sources = old

if __name__ == "__main__":
    unittest.main()
