"""YouTube adapter for the Chart Vallenato (read-only, YouTube Data API v3).

Needs only an API key (`YOUTUBE_API_KEY`) restricted to "YouTube Data API v3"
in Google Cloud — no OAuth, because the chart only reads public data and
never uploads or changes anything on YouTube. Quota cost per call is 1 unit
(`playlistItems.list`, `videos.list`, `channels.list`), so the daily refresh
of a few dozen channels stays far below the free default of 10,000 units.
"""
