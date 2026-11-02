# Channels live summary

You watch a WeChat Channels live stream in desktop WeChat (yours or someone else's) without listening the whole time: Nuttle
transcribes what the host says, one minute at a time, and keeps the comments; during or after the stream, an Agent sums up
what was said, what was sold and what viewers asked.
The bridge is only a bridge: this is a prompt template for your Agent; the analysis happens in the Agent. **No commenting, liking or ordering.**

## Requires

- Platform pack `weixin` 0.4+ (cards `weixin/live-speech`, `weixin/live-comment`)
- "WeChat Channels full data" plugin 0.10+, with the "WeChat Channels" plugin enabled
- Settings → Speech-to-text: a local model or an online service (without it you get comments only, no speech)
- You are in the live room in desktop WeChat and keep it open (transcription stops within 90 seconds after you leave)

## Fields

Speech `live_speech`: `id, live_id, content (what the host said in that minute), secs, create_time (segment start, seconds)`

Comments `live_comment`: `id, live_id, seq (order), nickname, user_id, content, identity (3 = host or moderator, 1/2 = viewer), create_time (when received, seconds)`

## Agent prompt template

Give the whole block below to your Agent:

```
Use Nuttle's MCP tools to summarize a WeChat Channels live stream I'm watching. Only use data already recorded; don't try to fetch anything.

Steps:
1. Call query_entities(platform="weixin", kind="live_speech", order_by="create_time", desc=false, limit=200) for the speech;
   list each live_id (start and end time, number of segments) and by default summarize the latest one, using keyword=<live_id>.
   If there are more than 200 segments, page on with since until done.
2. Do the same for kind="live_comment" (keyword=<live_id>, order_by="create_time"). identity=3 is typed by the host or a
   moderator — often selling points, prices, specs — treat it as the host speaking; the rest are viewers.
3. Read the speech in time order (transcripts have homophone and number errors; read in context, mark quotes as "transcript") and work out:
   - Timeline: every 10–15 minutes, what was covered (which product / topic)
   - Products: name, spec, live price, list / comparison price, gifts, link number ("link #X"), time- or stock-limited claims
   - Know-how: methods, experience and industry information that stand on their own once the sales talk is removed
   - Viewer concerns: questions, worries and requests repeated in comments (drop "joined" and spam slogans), and whether / how the host answered
4. Output:
   - One sentence on what this stream was
   - Timeline
   - Products (table)
   - Know-how
   - Top 5 viewer concerns (with the original comments)
   - Closing lines the host used (2–3 verbatim quotes)

Rules: for prices and specs, the host's typed text (identity=3) wins over speech numbers, which may be mistranscribed; list both when they
disagree. Quote comments verbatim. Don't invent anything that wasn't in the stream. Don't change or delete any mapping.
```

## Known limits

- Only the time you were in the room is recorded.
- Speech is machine-transcribed: homophones, numbers and brand names may be wrong, more so over loud background music.
- Joins ("joined"), order notices and gifts are not comments; viewer and like counts are in the raw endpoint `/nuttle/wxlive/GetLiveMsg` (`curParticipantCount`, `curLikeCnt`).
