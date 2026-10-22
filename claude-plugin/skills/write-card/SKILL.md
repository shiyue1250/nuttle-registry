---
name: write-card
description: Turn a website the user has browsed into a Nuttle mapping card, and (only with the user's explicit approval) publish it as a community pack from the user's own GitHub repository. Use when the user asks to support a new site, extract structured data from a page they browsed, "make a card", "写卡", "把这个网站接进来", or share their mapping with others.
---

# Write a Nuttle mapping card

A mapping card turns one JSON API response the user's browser already loaded into structured entities. The spec is https://github.com/shiyue1250/nuttle-registry/blob/main/SPEC.md — read it if anything below is unclear.

## Ground rules (from the spec — do not break them)

- **Passive and read-only.** Work only with data Nuttle has already captured while the user browsed. Never replay, script or schedule requests, and never ask the user for cookies, tokens or passwords.
- **Pure data.** A card is a JSON file of field paths. Do not put code in it.
- **Ask before anything public.** Creating a public repository or a release publishes the card and its fixture. Show the user exactly what will be published and wait for an explicit yes.

If the `nuttle` MCP tools (`list_endpoints`, `sample_raw`, `add_mapping`, …) are not available, the Nuttle desktop app is not running — ask the user to start it and enable the target site in its "采集范围 / Capture scope" page.

## 1. Find the endpoint

1. Ask the user what they want (for example "my order list in the Shopify admin", "comments under a note").
2. If it may not be captured yet, ask them to open that page and scroll or page through it, then call `wait_for_capture` to see new captures arrive.
3. Locate the endpoint: call `search_raw` with a value the user can see on the page (a product name, an order number). Fall back to `list_endpoints`.

## 2. Read the structure

Call `sample_raw` for that path. Identify:

- `item_path`: dot path from the response root to the array of items (`data.list`); empty string if the response itself is the array.
- A stable `id` field for each item — required for de-duplication.
- Useful fields. Watch units: prices often in cents (`price/100`), rates scaled by 10000 (`rate/10000`), timestamps in milliseconds (`create_time/1000`).

Path syntax: `a.b.c`, numeric segments index arrays (`images.0.url`), `/N` divides (rounded to 2 decimals), output names starting with `extra.` keep the whole value, `$path` / `$host` read the request context.

## 3. Register and verify

1. `add_mapping` with `pattern` = a distinctive path segment of the endpoint, `item_path`, `fields` (must include `id`), `kind` = `record` (use `product` only for product listings that use the product field names in the tool description).
2. `query_entities` (filter by `source=<rule name>`) for 2–3 items and compare them with what the user sees on the page — especially amounts, percentages and dates. Fix with another `add_mapping` call until they match.

## 4. Export the card and redact the fixture

1. `export_mapping` with the `pattern`, a pack id as `platform` (lowercase, e.g. `shopify-admin`) and the `entity` type (e.g. `order`). It writes `<name>.json` and `<name>.fixture.json` and reports what was replaced with placeholders.
2. Open the fixture. Besides the automatic placeholders, replace **third-party content** — other people's comment text, locations, real ids that identify a person — in both `response` and `expected` with the same placeholder strings. Make sure no cookie, token or `Authorization` value is present.
3. Edit the card: add `"apiVersion": 1`, `"locales": {"zh": {...}, "en": {"name": "...", "description": "..."}}`, and `"jsonld": {"@type": "<schema.org type>"}` (Comment, Product, Order, Review, …).

## 5. Package as a community pack

The `nuttle` command is the desktop app executable. If it is not on PATH, ask the user where Nuttle is installed.

```bash
nuttle card new <dir> <pack-id> "<*.domain.com>" "<display name>"   # only if the user has no pack repo yet
# copy the card and fixture into <dir>/mappings/
nuttle card lint <dir>     # fix every FAIL; read every WARN
nuttle card replay <dir>   # every card must report OK
```

Optionally add `endpoints` labels to `platform.json` (`[{"match": "<path segment>", "label": "what this endpoint returns"}]`) so other users know what each endpoint is for.

## 6. Publish (only after the user says yes)

Summarize for the user: the repository name, that it will be **public**, the pack id, domains, each card, and the fixture files. Wait for explicit approval. Then:

```bash
cd <dir>
git init && git add -A && git commit -m "feat: <pack-id> pack"
gh repo create <owner>/<repo> --public --source . --push
gh repo edit <owner>/<repo> --add-topic nuttle-pack
gh release create v<version> --title "v<version>" --notes "<what the cards extract>"
```

The release tag must equal `platform.json`'s `version` (with an optional `v`). The registry discovers new releases daily; the pack then appears in Nuttle's market with a "Community" badge.

## Updating a published pack

Bump `version` in `platform.json` (and the changed card's `version`), run `card lint` and `card replay`, commit, and create a new release. Never move an existing tag.
