# Amazon variation comparison

A person opens the detail pages of a few candidate products; the Agent rolls each product's color variations and availability into one comparison table and points out where the variation coverage differs.
Prices are not in this data (see "Known limits") — this recipe answers "whose variations are more complete, and which colors are out of stock".

## Requirements

- Platform pack `amazon` (mapping card `amazon/dp-twister` ≥ 0.2.0, entity kind `variation`)
- The Amazon site is turned on in the console under "Settings → Capture scope"
- The person opens product detail pages on amazon.com (`/dp/<ASIN>`); the variation data embedded in the page is captured without clicking anything

## Fields of a variation entity

`id (variation ASIN), label (color name), state (SELECTED / AVAILABLE / UNAVAILABLE …), page_path (the page it came from, like /dp/<parent ASIN>/_dom/a-state:…), extra.hidden`

Take the parent product ASIN from `page_path`: the 10 characters after `/dp/`.

## Agent prompt template

```
Use Nuttle's MCP tools to read the variation data from the Amazon product pages I've opened on amazon.com, and compare the variations. The data only comes from pages I've already opened — do not try to fetch anything.

Steps:
1. Call query_entities(platform="amazon", kind="variation", limit=500).
2. Group by the parent ASIN in page_path (regex /dp/([A-Z0-9]{10})). Each group is one product.
3. For each product count: total variations, available (state is AVAILABLE or SELECTED), unavailable, and the list of color names.
4. Output one comparison table: parent ASIN | variations | available | unavailable | colors. Then point out:
   - which product has the most complete variation coverage and which is out of stock the most
   - colors that only one product offers (set difference on color names)
5. If I open more product pages I'll say "again" and you rerun step 1; or call wait_for_capture(path_contains="twister-sort-filter", timeout_secs=60) to wait for me to open the next one.

Constraints: do not conclude which product "sells better" — this data has no price or sales; do not modify or delete any mapping.
```

## Known limits

- `desktop-twister-sort-filter-data` only has dimension info, not per-variation price or stock; prices need another card once the variation-switch request is captured.
- Only the `color_name` dimension is covered; a size with a single value does not show up as a variation.
- A variation ASIN has exactly one entity; opening the same product page again overwrites rather than accumulates.
