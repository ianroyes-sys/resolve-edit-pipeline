# Footage-to-film workflow

DaVinci Resolve Studio is the editor and finishing system. Local scripts handle inventory, verified ingest, review sheets, transcription, sound stems and QC. Editorial judgment stays in the loop: focus, performance, story relevance and pacing can't be settled by filenames or blur scores.

Alternatives considered: a pure FFmpeg edit (good for analysis, proxies and audio stems, but it can't reproduce Resolve's Film Look Creator) and a Resolve MCP server (simplifies access, but doesn't remove the limits of the installed scripting API). Calling the installed SDK directly avoids an extra server for the same calls.

## Starting a job

Create a job folder and a new Resolve project. Never reuse an existing commissioned timeline without checking who owns it. Supply: footage location, event or subject, the feeling you want, delivery orientation and length, reference projects, and preferred music. If the format is unspecified, infer a reversible first-cut format from the footage and say so.

1. **Discover and ingest.** Inventory footage and sidecars, resolve duplicate names with relative paths plus hashes, check storage, copy the card structure and verify SHA-256 (`pipeline/inventory.py`, `pipeline/ingest.py`). Keep originals and every rejected clip. Never erase or format a card.
2. **Learn the style.** Separate finished exports from camera files, proxies, tutorials and variants. Review contact sheets across the archive, then study the closest references in depth (`pipeline/contact_sheets.py`, `pipeline/style_analysis.py`). Record coverage honestly. Scene-change counts are estimates, not exact edit points.
3. **Cull.** Sample several points in every clip, inspect promising ranges closely, and label usable ranges with in/out times and story roles (`pipeline/review_card.py`, `pipeline/motion_screen.py`). Camera thumbnails alone are not enough. Separate technical problems from editorial exclusions. Keep alternatives and handles.
4. **Select music.** Compare mood, development, edit points and vocals against speech. Record the source path and licensing status. Map intro, build, peak and ending. A track used in an earlier project is a style reference, not proof of rights.
5. **Build the story.** Write the plan (`examples/edit-plan.example.json`), check it (`pipeline/verify_edit_plan.py`), then assemble (`resolve/build_timeline.py`). Get the emotional arc right before decorating transitions. Favor detail, action and reaction. Keep speech in context and in sync where it's shown. Mix brisk sequences with longer holds.
6. **Design sound.** Keep dialogue and useful location audio. Add restrained library effects only when the picture justifies them. Dialogue, natural sound, music and SFX stay on separate tracks; music ducks around speech (`sound/build_stems.py`). Measure loudness and true peak, then listen to the whole mix.
7. **Grade.** Identify camera gamut and gamma from sidecars. Inspect existing Film Look Creator settings instead of guessing from finished pixels (`grades/`). Saved looks that already transform S-Log3 to Rec.709 must receive log footage directly, with no second project or CST transform. Balance per shot in clip nodes and apply the shared look in a group post-clip graph. Keep titles outside the log-input group.
8. **Verify and deliver.** Check timeline item counts, timing, gaps, offline media, source ranges, framing, color continuity, titles and audio. Export a playable review copy and an editable DRP (`resolve/render_review.py`), then inspect the render itself (`pipeline/qc_render.py`). Never call a rough cut a verified final, or a machine transcript an auditioned quote.

## Feedback and motion gate

Read `EDITING-PREFERENCES.md` and the job's feedback file before culling. Every selected interval needs temporal review from in to out, with handles. Record camera movement, reset points and the exact approved range. Motion numbers and contact sheets are triage; check rapid frame changes and normal-speed playback before claiming a shot is steady. Never keep an unstable tail just for its dialogue. A failed range is trimmed or replaced before assembly.

Before locking, check consecutive shots for duplicate story purpose, check the important-participant list against the timeline, and cut material that breaks the requested tone. Don't pad to hit a runtime. Rebuild sound automation after picture changes so old dialogue and applause never play at stale positions.

After feedback: versioned evidence, then a durable rule or job-specific correction, then the actual edit, then a regression check (`verify_edit_plan.py` with an updated constraints file), then candid verification. Passing the script is not a substitute for watching and listening.

## Working with agents

Only one agent drives Resolve at a time. Other agents can analyse media or prepare assets in separate folders; the primary editor owns live timelines and rendering. Check the installed Resolve version and API instead of assuming the newest features. Confirm return values and the exported output. Test grade imports in an isolated project before touching the working film, and never repeat an import that crashed Resolve.

## References

- Installed Resolve SDK docs: `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/README.txt`
- https://github.com/samuelgursky/davinci-resolve-mcp (serialized grade research, DRX wrapper structure)
