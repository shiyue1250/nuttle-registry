# Official Account viral-article breakdown

A person reads a batch of WeChat Official Account articles in one niche (accounts they follow, competitors, viral pieces); the Agent breaks down, from the articles they have opened, the headline formulas, angles, structures and opening hooks into a reusable writing checklist.
The bridge stays a bridge: this recipe is a prompt template for the Agent and the analysis happens in the Agent; **it never posts, comments or likes**.

## Requirements

- Platform pack `weixin-mp` (mapping card `weixin-mp/article`; entity kind `article`)
- The Official Accounts card under Plugins shows "Enabled" (with the "WeChat Official Account articles" plugin)
- The person has opened these articles in WeChat for PC or a browser (only opened articles are recorded)

## Fields

Article `article`: `id, title, account, author, create_time (seconds), desc (summary), content (plain text), image_count, original, url`

## Agent prompt template

Give the whole block below to the Agent as the task:

```
Use Nuttle's MCP tools to read the Official Account articles I have opened and break down how the viral ones are written. Only use recorded data — do not try to fetch anything.

Input: a niche or keyword (e.g. "workplace communication", "AI tools"), optionally a few account names.

Steps:
1. Call query_entities(platform="weixin-mp", kind="article", keyword=<keyword>, order_by="create_time", limit=50);
   if accounts are given keep only matching ones. List candidates (title, account, time, length, link).
2. Read each content and extract:
   - Headline formula: number / counter-intuitive / pain question / identity / promise…, one per article with the original title
   - Opening hook: what the first 3 sentences do (scene, conflict, data, question)
   - Structure: list / story + method / comparison…, with the subheading skeleton
   - Angle: which entry point it takes on the topic
3. Summarize: how often each headline formula appears and which account uses it most; the 3 most common structures; 5 reusable headline templates (with source articles).
4. Output:
   - Overview: articles read, accounts, time span
   - Headline formula table: formula | articles | examples (original title + link)
   - Hooks and structures checklist
   - 5 topic ideas for me, each with "based on which articles"

Rules: quote titles and text verbatim; don't invent anything not in the articles; don't change or delete any mapping.
```

## Known limits

- Only opened articles are recorded; read counts, likes and comments are not wired up yet.
- Image posts and shared videos have no body text, so content is empty.
