# X feedback triage

A person posts a call for feedback on X and opens their own post to read the replies; the Agent reads those replies, turns them into a ranked list of requests, and drafts replies for the person to review and post.
The bridge stays a bridge: this recipe is a prompt template for the Agent and the analysis happens in the Agent; **posting and replying is always the person clicking "Post" themselves**.

## Requirements

- Platform pack `x` (mapping cards `x/post`, `x/reply`; entity kinds `post`, `comment`)
- The "X" and "X posts and replies" plugins enabled (the X card under Plugins shows "Enabled")
- The person opens their own post on X (web or app) and scrolls through the replies; only replies they have seen are captured

## Fields

Post `post`: `id, title (text), author, handle, create_time (seconds), view_count, like_count, retweet_count, reply_count, quote_count, bookmark_count, url`

Reply `comment`: `id, post_id (the post it belongs to), reply_to ("0" = replies to the post, otherwise the id of the reply it answers), nickname, handle, content, like_count, reply_count, view_count, create_time (seconds), reply_to_nickname, image, url`

## Agent prompt template

Give the whole block below to the Agent as the task:

```
Use Nuttle's MCP tools to read the replies I have seen on X and triage the feedback on my call-for-feedback post. The data only comes from pages I have already viewed — do not try to fetch anything; never post, reply, like or DM on my behalf.

Input: the link to my post (https://x.com/<handle>/status/<post id>) or the post id.
If I didn't give one: call query_entities(platform="x", kind="post", keyword=<my keyword>) and ask me which candidate it is.

Steps:
1. Call get_thread(platform="x", kind="post", id=<post id>, limit=500) to get the post and its reply tree (nested replies are under replies).
2. Classify every reply with one main category (secondary ones allowed):
   - Feature request: something they want it to do (new feature, improvement)
   - Platform request: a platform or site they want supported
   - Question or concern: privacy, security, price, ease of use, platform rules
   - Wants to try: asks to try it, asks for a link, wants the waitlist
   - Support and other
3. Merge requests that mean the same thing; record how many people asked (unique handles) and total likes (sum of like_count); sort by people, then likes.
4. Quote 1–2 original replies per request (content verbatim, with @handle).
5. Draft replies for: replies with a concrete request or question, the top 5 by likes, and everyone who wants to try it. Rules:
   - Reply in their language; be specific and sincere — no marketing, no promised release dates; don't @ anyone unrelated to that reply.
   - Add a "reply" link to each draft: https://x.com/intent/post?in_reply_to=<reply id>&text=<draft, URL-encoded>
     When I open it, X shows the reply box already filled in, and I click Post myself.
6. For replies that need my judgement (whether and how to reply, whether to build it), add a separate table: to @handle | their reply | why it needs me | link.
7. Output:
   - Overview: replies captured / reply_count shown on the post / count per category
   - Request table: request | people | total likes | quotes
   - Platform request ranking
   - Questions and concerns, with a suggested consistent answer for each
   - Reply drafts: to @handle | their reply | draft | reply link
   - Remind me: keep scrolling the replies on X and say "update" for an incremental pass
8. When I say "update": call get_thread again, process only replies not seen before (compare by id), merge them into the request table and mark what's new.

Rules: don't make my decisions for me (whether to reply, build or star something is mine); quote verbatim; don't invent anything that isn't in the replies; don't change or delete any mapping.
```

## Known limits

- The bridge only stores pages the person has viewed: X shows only part of the replies at first; scrolling and "Show more replies" bring in the rest.
- Like counts and times are as of the moment you saw them; viewing again updates them.
- The reply link can only carry text; add images yourself in X's reply box.
