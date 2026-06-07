# Policy Scout — Visual README

## 1. Purpose

This document explains how to use the visual docs.

The visual set currently includes:

```text
VISUAL_PRODUCTION_PLAN.md
MERMAID_DIAGRAMS.md
```

The diagrams are written in Mermaid so they can be rendered by tools that support Mermaid, including many Markdown viewers, GitHub-compatible renderers, and documentation systems.

---

## 2. Why Mermaid First

Mermaid is useful here because it is:

- text-based
- version-control friendly
- readable by agents
- easy to revise
- renderable later into SVG or PNG
- good for architecture diagrams and flows

The diagrams should be treated as living technical documents, not final marketing art.

---

## 3. Rendering Options

Potential rendering paths:

```text
Markdown preview with Mermaid support
GitHub or GitLab Mermaid rendering
Obsidian Mermaid preview
Mermaid CLI export to SVG/PNG
Later custom visual design pass
```

---

## 4. Diagram Maintenance Rule

If the docs change, update the diagrams.

If a diagram shows behavior that is not in the docs, either:

1. update the docs, or
2. update the diagram.

Do not allow diagrams to drift.

---

## 5. Recommended Next Visual Work

After the Mermaid batch, useful next outputs include:

```text
1. clean SVG exports
2. 16:9 presentation diagrams
3. README hero architecture graphic
4. scenario cards
5. risk component matrix
6. severity/confidence matrix
7. mode behavior matrix
8. Scout Report anatomy graphic
```

---

## 6. Visual Doctrine

The diagrams should make the safety boundary visible.

The most important concept is not that Policy Scout has many modules.

The most important concept is that every risky action passes through a structured, auditable decision boundary.
