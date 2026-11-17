#!/usr/bin/env python3
"""Build the recipe site.

Reads every recipes/*.yml file and writes a static site to _site/:
  _site/index.html                 list of all recipes
  _site/<slug>/index.html          one page per recipe

Each recipe page includes schema.org Recipe JSON-LD, which is what
Safari / Siri use to recognize a page as a recipe.
"""
import html
import json
import pathlib
import shutil
import sys

import yaml

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "recipes"
OUT = ROOT / "_site"
STATIC = ROOT / "static"


def esc(s):
    return html.escape(str(s), quote=True)


def iso_minutes(m):
    """30 -> PT30M, 90 -> PT1H30M (ISO 8601 duration for schema.org)."""
    if m in (None, ""):
        return None
    m = int(m)
    h, mins = divmod(m, 60)
    return "PT" + (f"{h}H" if h else "") + (f"{mins}M" if mins or not h else "")


def human_minutes(m):
    m = int(m)
    h, mins = divmod(m, 60)
    parts = []
    if h:
        parts.append(f"{h} hr")
    if mins:
        parts.append(f"{mins} min")
    return " ".join(parts) or "0 min"


def page(title, body, head_extra="", depth=0):
    prefix = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{prefix}style.css">
{head_extra}
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


def ingredient_lines(r):
    """Ingredients may be a flat list or a list of {group, items} sections."""
    flat, sections = [], []
    for item in r.get("ingredients", []):
        if isinstance(item, dict) and "items" in item:
            sections.append((item.get("group"), item["items"]))
            flat.extend(item["items"])
        else:
            if not sections or sections[-1][0] is not None:
                sections.append((None, []))
            sections[-1][1].append(item)
            flat.append(item)
    return flat, sections


def step_lines(r):
    flat, sections = [], []
    for item in r.get("steps", []):
        if isinstance(item, dict) and "items" in item:
            sections.append((item.get("group"), item["items"]))
            flat.extend(item["items"])
        else:
            if not sections or sections[-1][0] is not None:
                sections.append((None, []))
            sections[-1][1].append(item)
            flat.append(item)
    return flat, sections


def render_recipe(slug, r):
    ingredients, ing_sections = ingredient_lines(r)
    steps, step_sections = step_lines(r)

    ld = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": r["title"],
        "recipeIngredient": [str(i) for i in ingredients],
        "recipeInstructions": [
            {"@type": "HowToStep", "position": n, "text": str(s)}
            for n, s in enumerate(steps, 1)
        ],
    }
    if r.get("description"):
        ld["description"] = r["description"]
    if r.get("servings"):
        ld["recipeYield"] = str(r["servings"])
    if r.get("category"):
        ld["recipeCategory"] = r["category"]
    if r.get("cuisine"):
        ld["recipeCuisine"] = r["cuisine"]
    if r.get("tags"):
        ld["keywords"] = ", ".join(r["tags"])
    if r.get("image"):
        ld["image"] = r["image"]
    for key, field in (("prep_minutes", "prepTime"), ("cook_minutes", "cookTime"), ("total_minutes", "totalTime")):
        v = iso_minutes(r.get(key))
        if v:
            ld[field] = v
    if "totalTime" not in ld and (r.get("prep_minutes") or r.get("cook_minutes")):
        ld["totalTime"] = iso_minutes(int(r.get("prep_minutes") or 0) + int(r.get("cook_minutes") or 0))
    if r.get("source"):
        ld["author"] = {"@type": "Person", "name": r["source"]}

    meta = []
    if r.get("servings"):
        meta.append(f"<li><span>Serves</span>{esc(r['servings'])}</li>")
    for key, label in (("prep_minutes", "Prep"), ("cook_minutes", "Cook"), ("marinate_minutes", r.get("rest_label", "Marinate"))):
        if r.get(key):
            meta.append(f"<li><span>{label}</span>{human_minutes(r[key])}</li>")

    def list_sections(sections, tag):
        out = []
        for group, items in sections:
            if group:
                out.append(f"<h3>{esc(group)}</h3>")
            out.append(f"<{tag}>" + "".join(f"<li>{esc(i)}</li>" for i in items) + f"</{tag}>")
        return "\n".join(out)

    notes = ""
    if r.get("notes"):
        n = r["notes"]
        items = n if isinstance(n, list) else [n]
        notes = "<section><h2>Notes</h2><ul>" + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul></section>"

    body = f"""
<p class="back"><a href="../">&larr; All recipes</a></p>
<article>
<h1>{esc(r['title'])}</h1>
{f'<p class="desc">{esc(r["description"])}</p>' if r.get('description') else ''}
{('<ul class="meta">' + ''.join(meta) + '</ul>') if meta else ''}
<section><h2>Ingredients</h2>
{list_sections(ing_sections, 'ul')}
</section>
<section><h2>Instructions</h2>
{list_sections(step_sections, 'ol')}
</section>
{notes}
</article>
"""
    head = '<script type="application/ld+json">\n' + json.dumps(ld, indent=2, ensure_ascii=False) + "\n</script>"
    if r.get("description"):
        head += f'\n<meta name="description" content="{esc(r["description"])}">'
    return page(r["title"], body, head, depth=1)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for f in STATIC.glob("*"):
        shutil.copy(f, OUT / f.name)
    (OUT / ".nojekyll").write_text("")

    recipes = []
    for path in sorted(SRC.glob("*.y*ml")):
        r = yaml.safe_load(path.read_text())
        if not r or not r.get("title"):
            sys.exit(f"{path}: missing title")
        slug = path.stem
        (OUT / slug).mkdir()
        (OUT / slug / "index.html").write_text(render_recipe(slug, r))
        recipes.append((slug, r))

    recipes.sort(key=lambda x: x[1]["title"].lower())
    items = "".join(
        f'<li><a href="{slug}/">{esc(r["title"])}</a>'
        + (f'<span>{esc(r["category"])}</span>' if r.get("category") else "")
        + "</li>"
        for slug, r in recipes
    )
    body = f"<h1>Recipes</h1>\n<ul class=\"index\">{items or '<li>No recipes yet.</li>'}</ul>"
    (OUT / "index.html").write_text(page("Recipes", body))
    print(f"Built {len(recipes)} recipe(s) into {OUT}")


if __name__ == "__main__":
    main()
