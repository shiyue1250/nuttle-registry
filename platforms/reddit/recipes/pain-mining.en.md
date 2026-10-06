# Reddit pain-point mining

A person browses subreddits and threads in a space (competitor discussions, "what do you use for…", rants); the Agent mines the posts and comments they have seen for recurring pains, unmet wants and current workarounds, with verbatim evidence, to find product direction.
The bridge stays a bridge: this recipe is a prompt template for the Agent and the analysis happens in the Agent; **it never posts, replies or votes**.

## Requirements

- Platform pack `reddit` (mapping cards `reddit/post`, `reddit/comment`; entity kinds `post`, `comment`)
- The Reddit card under Plugins shows "Enabled" (with the "Reddit posts and comments" plugin)
- The person browses relevant subreddits and search results on the Reddit website and opens busy threads; only what they have seen is recorded

## Fields

Post `post`: `id, title, content (body, only after opening the post), author, subreddit, score, comment_count, upvote_ratio, create_time (seconds), url`

Comment `comment`: `id, post_id, reply_to ("0" = replies to the post, otherwise the parent comment id), depth, nickname, content, like_count (score), create_time (seconds), is_op, url`

## Agent prompt template

Give the whole block below to the Agent as the task:

```
Use Nuttle's MCP tools to read the Reddit posts and comments I have seen, mine real user complaints, and help me judge a product direction. Only use data I have already browsed — do not try to fetch anything; never post, reply or vote on my behalf.

Input: a topic keyword (e.g. "note-taking app", "Shopify returns"), optionally a subreddit (r/xxx).

Steps:
1. Call query_entities(platform="reddit", kind="post", keyword=<keyword>, order_by="comment_count", limit=50) to find related posts;
   if a subreddit is given keep only matching ones. List the candidates (title, subreddit, score, comments, link).
2. For the 10 posts with the most comments, call get_thread(platform="reddit", kind="post", id=<post id>, limit=500) to get the comment tree.
3. Extract every complaint / want / workaround from post bodies and comments: type, verbatim quote, author, score, link.
   - Complaint: what existing products get wrong (slow, expensive, hard to use, missing features, data loss…)
   - Want: "I wish there was…", "is there a tool that…"
   - Workaround: what people use today (product names, their own scripts, spreadsheets…)
4. Merge items that mean the same thing; count people (unique authors) and total score; sort by people, then score.
5. Output:
   - Overview: posts read, comments read, subreddits covered
   - Pain table: pain | people | total score | representative quote (with link)
   - Unmet wants: want | people | quote
   - Workarounds: product / approach | mentions | praised for | complained about
   - Opportunity call: the 3 pains most worth building for, one-line reason each; mark weak evidence as "needs more threads"
6. For posts or comments I should read myself, call tag_entity(platform="reddit", kind=<post or comment>, id=<id>, tag="待核实", note="<one-line reason>").

Rules: quote verbatim with links; only use the tag "待核实" (to verify) — never "需求池" (backlog) or "忽略" (ignore), those are my calls; don't invent anything not in the data; don't change or delete any mapping.
```

## Known limits

- Only what was seen is recorded: listings show titles only, bodies need the post opened; only the first batch of comments loads until "more comments" is expanded.
- Scores and comment counts are as of the moment you saw them; viewing again updates them.
- Deleted or removed comments have no text.
