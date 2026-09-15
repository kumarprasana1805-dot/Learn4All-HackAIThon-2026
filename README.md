# Learn4All — National Level Final V16

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## V16 Topic Accuracy + Performance Engine

- Dynamic topic content uses a single high-confidence Wikipedia/MediaWiki page selected with topic + subject relevance checks.
- Obvious film/movie/song/actor/TV/game and disambiguation results are rejected.
- Search hits are no longer concatenated across unrelated pages.
- Source material is filtered for media/pop-culture contamination before becoming notes, video chapters, or quiz content.
- If a sufficiently relevant source cannot be verified, Learn4All withholds factual notes, quiz, and video instead of displaying unrelated or invented information.
- Curated/local topic packs continue to work offline.


## V10 Resource Engine

- **Notes:** known topics use the bundled curated classroom packs. Other topics use the MediaWiki/Wikipedia search + Parse API to retrieve source-backed page text, then cache the retrieved lesson locally.
- **Quiz:** rebuilt from the exact lesson sections displayed on the topic page. It produces up to 20 single-answer MCQs with four distinct options and a validated answer key. No fabricated answer bank is used when fewer than four factual sections are available.
- **Video:** creates a real MP4 from the same lesson sections using Pillow + FFmpeg/imageio-ffmpeg. The output uses H.264, yuv420p and fast-start MP4 settings for browser playback.
- **Caching:** retrieved topic lessons and generated videos are cached so repeat visits do not regenerate them unnecessarily.
- **Fallback:** when a source cannot be reached, the app does not claim that generic study advice is factual topic content. It clearly indicates that verified source material is unavailable.

## Important

For arbitrary topics, factual correctness depends on the retrieved source and should be checked against the prescribed school textbook/syllabus. The application intentionally avoids inventing topic facts when no source is available.


## V12 Cinematic Motion Polish
- Visual-only premium animation layer added across application pages.
- Smooth page entrance, scroll reveal, hover lift, button sheen/ripple, progress animation, quiz/video interactions, and subtle ambient motion.
- Login artwork receives subtle desktop parallax.
- Respects `prefers-reduced-motion` for accessibility.
- No application routes, data logic, resource engines, authentication, teacher controls, quiz logic, notes logic, or video logic were removed.


### V16 fixes
- Added high-confidence offline classroom packs for common ambiguous topics such as integration, matrix/matrices, and rectangle/rectangles.
- Added faster MediaWiki REST search metadata and reduced full-page parsing work.
- Added process-level topic-content caching and persistent negative caching to prevent repeated slow failed searches.
- Kept verified-content gating: unrelated or ambiguous sources are withheld rather than presented as facts.
- Reduced first-time generated-video rendering work while keeping browser-compatible MP4 output.
