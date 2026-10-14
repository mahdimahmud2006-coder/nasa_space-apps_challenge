# Desktop layout and date playback

Updated 2026-10-14. This update changes the viewer presentation and playback behavior. The scientific code, downloaded sources, radar results and environmental context outputs are preserved.

## Desktop layout

The pair-comparison viewer uses the desktop window height for its map workspace, with independently scrolling control and evidence panels. The map remains square inside a centered canvas, preserving alignment between imagery, swipe controls and region geometry. Wider desktop displays use more horizontal space; smaller displays retain the stacked responsive layout.

The time-series viewer now has a compact timeline toolbar, a larger workspace relative to the page header, an independently scrolling desktop evidence panel, and collapsible source and recovery details. Its canvas preserves the same square ground footprint at every window size. The selected acquisition date stays visible on the map. Charts highlight the selected date when they contain a measurement for it.

## Date playback

Open `http://127.0.0.1:8000/timeseries.html`, select the start/end acquisitions and press **Play range**. Controls include:

- Play / pause and return to the selected range start.
- Playback start and end dates drawn exclusively from saved acquisitions.
- 0.5×, 1× and 2× speed: 3, 1.5 and 0.75 seconds per saved date.
- Optional looping, previous/next controls, date buttons and a scrubber.
- Space to play/pause outside form controls; left/right arrows while the map is focused.

The home viewer also has **Play date range**, which opens the timeline and starts playback through the saved range. Playback stops when the page is hidden or navigated away from. Manual date selection pauses it. Selecting a new map layer pauses playback so the new layer can be inspected; pressing Play continues through the dates using that layer.

Maps and evidence commit together only after the selected observation and overlay have decoded. The next playback timer starts after rendering finishes, preventing skipped frames during slow loads. Missing local assets stop playback and display an error. Local observation previews are cached after first load. A short crossfade softens acquisition changes and is disabled for reduced-motion preferences.

Playback shows discrete saved observations. No intervening daily radar measurements or scientific interpolation are generated. Persistence, recovery and static terrain overlays are explicitly described as series-wide or fixed layers; acquisition-specific rainfall layers follow the selected date.

## Verification

- Existing Python science/API suite: **96 passing**, four existing Rasterio pending-deprecation warnings.
- Playback controller: **10 passing Node tests**, covering range traversal, replay, pause, queued callbacks, looping, manual seek/resume, single-date ranges, slow loading, cancellation, load errors and speed changes.
- JavaScript syntax checks pass for the main viewer, time-series viewer and playback module.
- HTML nesting is balanced, IDs are unique, and all **45 main-viewer** and **40 time-series** JavaScript-referenced IDs resolve.
- Eight generated routes/assets are served successfully through the local HTTP handler without network sockets. The `.mjs` module is served as JavaScript.
- Interactive browser/responsive visual verification and physical disconnected rehearsal remain pending; the previous browser policy block was not bypassed.

Run the playback tests with `make test-ui` (Node.js required for this development check). Viewing the demo still needs only Python and a browser; no Node.js installation, additional library or online service is required at runtime.

Start the demo with `make demo`, then refresh the page. These are static frontend changes, so an existing server using the current API can serve them without restarting. A hard refresh may help if an older tab retains its previously loaded JavaScript.
