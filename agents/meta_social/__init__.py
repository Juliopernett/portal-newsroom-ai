"""Meta (Facebook/Instagram) social reading adapters.

`client.MetaGraphSocialMediaReader` is what `app.api.dependencies.
get_social_media_reader` returns — a System User access token
(`META_ACCESS_TOKEN`) with `pages_read_engagement`/`pages_show_list`/
`instagram_basic`, plus `META_PAGE_ID`/`META_INSTAGRAM_BUSINESS_ACCOUNT_ID`,
configured 2026-08-20. `fake_reader.FakeSocialMediaReader` (every post
prefixed `[DEMO]`) is what tests use instead, via
`app.dependency_overrides` — nothing in production code should construct
it directly.
"""
