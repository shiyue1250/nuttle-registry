# Xiaohongshu comment insights

A person reads through note comments; the Agent aggregates them as they arrive, reports each note's themes, sentiment and open questions, and tags the comments worth digging into as `待核实` ("to verify") for the person to confirm.
Nuttle only stores the data: this recipe is a prompt template for the Agent — the analysis happens in the Agent, not in Nuttle.

## Requirements

- Platform pack `xiaohongshu` (mapping cards `xiaohongshu/note`, `xiaohongshu/comment-page`, `xiaohongshu/comment-sub`; entity kinds `note`, `comment`)
- The Xiaohongshu (RedNote) plugin is enabled on the console's Plugins page; the endpoints that matter are `/api/sns/web/v1/feed` (notes), `/api/sns/web/v2/comment/page` (comments) and `/api/sns/web/v2/comment/sub/page` (expanded replies)
- The person opens the Xiaohongshu web app, goes into a note, pages through the comments and clicks "expand replies" (guests only see the first page of comments; log in to page further)

## Fields of a comment entity

`id, note_id, content, like_count (string), create_time (seconds), ip_location, sub_comment_count (string), reply_count, user_id, nickname, head, extra.sub_comments, extra.pictures`; expanded replies also carry `reply_to` (the comment they answer) and `reply_to_nickname`

`like_count` is a string — convert it to a number before sorting.

## Agent prompt template

Give the whole block below to the Agent as the task:

```
Use Nuttle's MCP tools to read the Xiaohongshu (RED) comments I've viewed in the web app, and produce comment insights. The data only comes from pages I've already viewed — do not try to fetch anything. Comments are in Chinese; quote them in the original Chinese, and write your analysis in English.

Steps:
1. Call list_tags first and confirm the tag set contains 待核实 ("to verify").
2. Loop: call wait_for_capture(path_contains="comment/page", after_id=<the cursor returned last time>, timeout_secs=60).
   - If new > 0: call query_entities(platform="xiaohongshu", kind="comment", limit=500) and only process comments whose last_seen is later than the start of this round.
   - If timed_out: tell me "waiting for you to scroll", then wait another round; after 3 rounds in a row with no new comments, stop and output the summary.
3. Each round, group new comments by note_id and, for each note, summarize:
   - Themes: what the comments mostly talk about (at most 3, one sentence each, with how often each comes up)
   - Sentiment: how many are positive / negative / questions, and use like_count as a weight to say which voice gets more agreement
   - Open questions: questions users ask that the note doesn't answer — quote the comment content verbatim
   - Worth digging into: complaints, needs, comparisons with competitors. For each one call
     tag_entity(platform="xiaohongshu", kind="comment", id=<comment id>, tag="待核实", note="<one sentence on why it's worth a look>")
4. At the end output: a summary table per note + how many comments were tagged 待核实 this time + a reminder for me to confirm them on the console's "Data" page; I'll change the confirmed ones to 需求池 ("needs pool").
5. Later, when I say "show the needs pool", call query_entities(platform="xiaohongshu", kind="comment", tag="需求池") and group the needs by my notes (tags[].note).

Constraints: never tag comments 需求池 or 忽略 ("ignore") — those are my decisions; do not modify or delete any mapping; keep quoted comments verbatim, never rewrite them.
```

## Output example (structure)

| note_id | Comments | Themes | Sentiment | Open questions | To verify |
|---|---|---|---|---|---|
| 6aa0e3…bbc3 | 23 | When are you coming to Australia (7)… | positive 15 / question 6 / negative 2 | “有没有 26 寸的” (is there a 26-inch one?) | 3 |

## Known limits

- Nuttle only stores pages the person has viewed; comments exist only up to the page the person scrolled to.
- `wait_for_capture` is a long poll — it only blocks while the Agent is calling it; Nuttle never pushes.
- The few replies shipped with a top-level comment stay in `extra.sub_comments`; replies loaded by "expand replies" are separate entities (also `comment`, with `reply_to`). For a note with its whole comment tree, use get_thread(platform="xiaohongshu", kind="note", id=<note id>).
