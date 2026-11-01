# Functional Benchmark v1: Big Sites (2026-10-31)

Method: 20 fresh users per site, parallel on GitHub Actions.
Pass = the media was VERIFIED playing (video/audio time advanced), not just clicked.
Every user had a unique IP in every run (20/20, all three runs).

## Results

| Site | Passed | Verified playing | Main failures |
|------|--------|------------------|---------------|
| YouTube | 0/20 | 0 | 10 x video opened but stayed paused at 0s. 10 x click element not found |
| Rumble | 0/20 | 0 | 20 x video link not found on home page |
| Spotify | 0/20 | 0 | 20 x no media element on search page |

Runs: YouTube 41226865277, Rumble 41227549209, Spotify 41228153695.

## Honest diagnosis (what is proven, what is not)

YouTube:
- Half the users DID reach a watch page. The video element existed but never started.
  Our task had no explicit play click. It relied on autoplay. That is our task fault first.
  A bot overlay is possible but NOT proven.
- Half failed the click: the alternative selector `#video-title-link` found nothing.
  The main selector worked. The variant system caught a bad selector. Our fault, proven.

Rumble:
- Home page loaded for all 20. Our selector `a[href^="/v"]` found no video link.
  Wrong selector is the first suspect (links may be absolute URLs).
  A challenge page is possible but NOT proven.

Spotify:
- Search page loaded, scrolled, but no media element exists until a track is clicked.
  Our task never clicked a track. Our fault, proven.
  Full play also needs login. That wall is real and still untested at the track level.

Big instrumentation gap (ours):
- The runner saves screenshot and page text only on success.
  So failed runs cannot show what page the user actually saw.
  Every "blocked or not" question above is partly a guess because of this. Fix first in v2.

## Bench v2 plan

1. Runner: save screenshot, page text, and final URL on FAILURE too.
2. Scout each site with 1 user first. Find the real selectors on the live page.
3. Add normal play steps: click the video / play button, click a track on Spotify.
4. If a login prompt or captcha appears, record it as the site result.
5. Rerun 20 users per site. Then pass and block numbers will mean something.

Score today, plain: 0 of 60 verified plays. The fleet, IPs, variants, and reporting work.
The site tasks and failure evidence do not. That is what v2 fixes.

---

# Functional Benchmark v2 (2026-11-01)

Fixes from v1 were applied first:
- Runner now saves screenshot, page text, final URL and fingerprint on FAILURE too.
- New scout step `dump_links` records live page structure (links, buttons, inputs, media).
- New `click_media` step: a normal click on the video element.
- Each site was scouted with 1 user before the 20 user run.

## Scout findings (1 user each, all proven from live page data)

YouTube: search works, result links are `a#video-title`. Watch page text says:
"Sign in to confirm you're not a bot. This helps protect our community."
Video element: readyState 0, paused, time 0. The player never loads media.

Rumble: home page is a Cloudflare challenge, title "Just a moment...",
text "Performing security verification... verifies you are not a bot", with a Ray ID.
No video links exist on that page. The v1 selector was never the main problem.

Spotify: search works, no block. Track links are `a[href^="/track/"]`.
No media element exists until play is pressed.

## v2 results (20 users per site, unique IPs 20/20 in every run)

| Site | Passed | Proven reason |
|------|--------|---------------|
| YouTube | 0/20 | All 20 reached the watch page and clicked the player. All 20 pages carried the bot check text. Media time stayed 0. Site block, proven from page text. Run 41300247718 |
| Rumble | 0/20 | All 20 got the Cloudflare security verification page. Site challenge, proven from page text. Run 41300667984 |
| Spotify v2 | 0/20 | All 20 opened a track. The play button existed in the page but was "not visible", so clicks timed out. Run 41301112098 |
| Spotify v3 (scroll fix) | 0/20 | Scroll made the play button visible, all 20 clicked it. Spotify answered by adding `#login` to the URL and creating no media. Login wall at play, proven. Run 41301543257 |

## What v2 proves

The v1 score (0/60) mixed our faults with site defenses. v2 separates them:
- Our v1 faults are fixed: selectors, play steps, track click, failure evidence.
- What remains is site side, with evidence per user: YouTube bot check,
  Rumble Cloudflare challenge, Spotify login wall.
- A testing tool's honest job on such sites is to measure and report this.
  Defeating these checks is a different activity and is not part of this system.
