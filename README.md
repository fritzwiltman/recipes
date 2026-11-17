# Recipes

My recipe site, published with GitHub Pages at **https://fritzwiltman.github.io/recipes/**.

Every recipe page includes [schema.org Recipe](https://schema.org/Recipe) structured data. Safari and Siri use that data to recognize a page as a recipe, so you can open a recipe in Safari and send it to Siri or HomeView.

## Adding a recipe

Add a file to `recipes/`, for example `recipes/garlic-butter-steak.yml`. The file name becomes the URL: `.../recipes/garlic-butter-steak/`. When you push to `main`, GitHub Actions rebuilds the site.

```yaml
title: Garlic Butter Steak
description: One-line summary.
category: Main
cuisine: American
servings: 2
prep_minutes: 10
cook_minutes: 15
marinate_minutes: 60   # optional, shown on the page only
tags: [beef, quick]
source: Mom            # optional

ingredients:
  - 2 ribeye steaks
  - 3 tbsp butter
  # or group them:
  # - group: Sauce
  #   items: [1 cup cream, 1 tsp salt]

steps:
  - Pat the steaks dry and season.
  - Sear 4 minutes per side.

notes:                 # optional
  - Works on the grill too.
```

Build locally with `pip install pyyaml && python build.py`, then open `_site/index.html`.
