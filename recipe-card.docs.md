---
title: Recipe Card
description: Turn a recipe URL into a Cooking for Engineers-style card, with ingredients down the left and steps as merged cells, plus scaling and metric/US conversion.
tags: [cooking, parsing]
---

Paste a recipe URL. The page is fetched through a public CORS proxy, falling
back to the Wayback Machine if the site is down. The recipe is read from the
page's schema.org `Recipe` data, the same structured data
[Mealie](https://mealie.io/) and
[recipe-scrapers](https://github.com/hhursev/recipe-scrapers) rely on, with
microdata and "Ingredients"/"Instructions" headings as fallbacks. You can also
paste page HTML, JSON-LD, a Mealie recipe JSON export or plain text.

Ingredient lines are parsed with
[parse-ingredient](https://github.com/jakeboone02/parse-ingredient). Each step
is matched to the ingredients it names, and steps that continue earlier work
are chained together. The result is the tabular layout
[Michael Chu](https://www.cookingforengineers.com/) used on Cooking for
Engineers: one row per ingredient, and each operation a cell spanning the rows
it combines. The layout algorithm follows
[recipeGrid](https://github.com/18sg/recipeGrid).

Matching steps to ingredients is heuristic. When it gets something wrong,
**Edit structure** shows the tree as indented text you can fix by hand.

Known limits: quantities written inside step text aren't scaled, volume isn't
converted to weight (cups of flour stay a volume), and public CORS proxies
come and go. Fetch settings accept your own proxy URL.
