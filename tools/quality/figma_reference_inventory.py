"""Offline, ordered Figma reference contracts; never a completion verifier."""

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REFERENCES = Path("C:/Users/yedek/Desktop/Figma tasar\u0131m")
TRACKED_TAGS = {"title", "h1", "h2", "h3", "h4", "button", "label", "summary",
                "a", "th", "td", "textarea", "option"}
INPUT_TAGS = {"input", "select", "textarea", "img"}


class ReferenceHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.elements = []
        self.inputs = []
        self.dependencies = []
        self.skip_depth = 0
        self.code_blocks = []
        self.active_code = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style"}:
            self.skip_depth += 1
            entry = {"tag": tag, "attributes": attrs, "chunks": []}
            self.code_blocks.append(entry)
            self.active_code.append(entry)
        if tag in INPUT_TAGS:
            self.inputs.append({"tag": tag, "attributes": attrs})
        if tag in {"script", "link", "img"}:
            uri = attrs.get("src") or attrs.get("href")
            if uri:
                self.dependencies.append({"tag": tag, "uri": uri})
        if tag in TRACKED_TAGS:
            entry = {"tag": tag, "attributes": attrs, "chunks": []}
            self.stack.append(entry)
            self.elements.append(entry)

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.skip_depth = max(0, self.skip_depth - 1)
            if self.active_code:
                self.active_code.pop()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        for block in self.active_code:
            block['chunks'].append(data)
        if not self.skip_depth:
            for item in self.stack:
                item["chunks"].append(data)

    def contract(self):
        return {
            "elements": [{"tag": item["tag"], "attributes": item["attributes"],
                          "text": " ".join("".join(item["chunks"]).split())}
                         for item in self.elements],
            "inputs": self.inputs,
            "dependencies": self.dependencies,
            "design_code_blocks": [{"tag": block['tag'], "attributes": block['attributes'],
                                    "text": ''.join(block['chunks'])}
                                   for block in self.code_blocks],
        }


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_file(path, reference_root):
    evidence = {"path": path.relative_to(reference_root).as_posix(),
                "sha256": fingerprint(path), "size_bytes": path.stat().st_size}
    if path.suffix.lower() == ".html":
        parser = ReferenceHTML()
        with path.open("r", encoding="utf-8-sig") as stream:
            for chunk in iter(lambda: stream.read(16384), ""):
                parser.feed(chunk)
        parser.close()
        evidence["contract"] = parser.contract()
    elif path.suffix.lower() == ".md":
        with path.open("r", encoding="utf-8-sig") as stream:
            evidence["lines"] = [line.rstrip("\r\n") for line in stream]
    elif path.suffix.lower() == ".png":
        with Image.open(path) as screenshot:
            evidence["image"] = {"width": screenshot.width, "height": screenshot.height,
                                 "mode": screenshot.mode}
        evidence["visual_review"] = "not_proven_by_inventory"
    return evidence


def inventory(reference_root):
    reference_root = Path(reference_root)
    parts = []
    for part in range(1, 8):
        folders = [folder for folder in reference_root.iterdir() if folder.is_dir()
                   and re.fullmatch(r"part\s*" + str(part), folder.name, re.IGNORECASE)]
        if len(folders) != 1:
            raise ValueError("Expected one reference folder for part " + str(part))
        files = sorted((path for path in folders[0].iterdir()
                        if path.suffix.lower() in {".html", ".md", ".png"}),
                       key=lambda path: (path.stem.strip().casefold(), path.suffix.lower()))
        screens = {}
        for path in files:
            key = path.stem.strip().casefold()
            screen = screens.setdefault(key, {"name": path.stem.strip(), "artifacts": [],
                                               "matching_status": "unverified"})
            screen["artifacts"].append(inspect_file(path, reference_root))
        parts.append({"part": part, "folder": folders[0].name, "screens": list(screens.values())})
    return {"status": "inventory_only", "reference_root": str(reference_root),
            "parts": parts, "screens": sum(len(part["screens"]) for part in parts),
            "artifacts": sum(len(screen["artifacts"]) for part in parts for screen in part["screens"]),
            "completion": "Requires visual and functional evidence for desktop, web, and mobile."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--references", type=Path, default=DEFAULT_REFERENCES)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "artifacts" / "figma_reference_inventory.json")
    args = parser.parse_args()
    report = inventory(args.references)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "screens": report["screens"],
                      "artifacts": report["artifacts"], "report": str(args.output)}))


if __name__ == "__main__":
    main()
