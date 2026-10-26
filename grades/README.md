# Recovering Film Look Creator grades from old projects

`extract_grades.py` opens exported `.drp` archives offline, finds every serialized grade `Body`, decodes it (`0x81` = Zstandard, `0x80` = stored), and flags bodies containing the plugin id `com.blackmagicdesign.resolvefx.filmlook`. Each unique Film Look body is written unchanged into a `Resolve_Color_Exchange` wrapper, and `grade-inventory.json` records hashes, source members, group/version ids and readable strings.

## Native-import candidates

The `Resolve_Color_Exchange` wrappers are analysis artifacts. Importing one of them was followed by Resolve disconnecting, so don't import them. `native_wrappers.py` writes separate `*-native.drx` candidates using Resolve's own `Gallery::GyStill` structure with a nested `pClipFullVer/ListMgt::LmVersion`, matching what Resolve's gallery exporter produces. Grade bytes stay identical.

Validate candidates only in a disposable project (`resolve/validate_grade.py`) after saving valuable work. Check `GetToolsInNode` and render a representative frame before using a look across a film.

## Offline group transfer

`transfer_group.py` copies one group's Post Clip Grade from a reference `.drp` into a named group of a new `.drp`. It patches only that slot's `Body` and `HasCorrection`, then proves every other archive member is byte-identical and that reverting the two values reproduces the original XML. Import the result into Resolve to finish.

## Don't transform twice

Film Look Creator grades carry their own input/output strings, for example:

- `inputColorSpace`: `SGAMUT3CINE_COLORSPACE`
- `inputGamma`: `SONY_SLOG3_GAMMA`
- `outputColorSpace`: `REC709_COLORSPACE`
- `outputGamma`: `TWOPOINTFOUR_GAMMA`

When a saved look already converts S-Log3 to Rec.709, feed it log footage. Don't also convert upstream with a CST or project color management. Applying looks as group post-clip grades leaves room for per-shot balancing upstream.

## Limits

This proves grade preservation and plugin presence, not successful import or the rendered look. Numeric OFX parameters are never guessed or rewritten.
