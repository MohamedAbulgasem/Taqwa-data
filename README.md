# Taqwa-data

Quran recitation audio for **[Taqwa](https://github.com/MohamedAbulgasem/Taqwa)**, a free,
ad-free, open-source Islamic app.

This repository holds three things and nothing else:

| What | Where |
|---|---|
| The catalogue the app reads | [`manifest.json`](manifest.json) |
| The audio itself | GitHub **Releases**, one release per reciter (`audio-<id>-v1`), 114 assets each |
| The pipeline that produced both | [`tools/`](tools/) |

No audio is committed to git. Each release carries 114 `.taqa` containers, one per surah,
each holding that surah's per-ayah MP3s exactly as they were downloaded.

---

## Where the audio comes from

The **Islamic Network / alquran.cloud** per-ayah corpus at `cdn.islamic.network`
(`https://cdn.islamic.network/quran/audio/{folder}/{reciter}/{globalAyah}.mp3`, global ayah
1–6236). Every file is mirrored **byte for byte**: no re-encoding, no re-tagging, no
normalisation, no trimming. That is deliberate — the licence below covers redistribution
"at the bitrates we publish", so the safest thing to redistribute is precisely the bytes
that were published.

A handful of objects answer HTTP 502 persistently from that CDN's origin. Where that
happened, the file was taken from **everyayah.com** at the same bitrate instead. This is
sound: the Islamic Network corpus *is* the everyayah corpus with rewritten ID3 tags, and
the pipeline proves it per reciter before falling back — it downloads three ayahs it
already holds from everyayah and requires the decoded audio to be MD5-identical. Any such
substitution is listed in the release notes of the affected reciter.

The CDN's bitrate *folder* name is not always the true bitrate (Maher Al Muaiqly's `/128`
is really 64 kbps; Saud Ash-Shuraim's `/64` is really 128 kbps). `manifest.json` records
the **measured** bitrate, not the folder name.

---

## The `.taqa` container, version 1

One file per (reciter, surah). Not a zip: iOS has no zip reader in Foundation and
Kotlin/Native would need a cinterop for one. This is a header, a JSON index and the MP3s.

```
offset  size      meaning
0       4         "TAQA", ASCII
4       1         version = 1 (u8)
5       3         reserved, all zero
8       4         indexLength, u32 big-endian
12      indexLength   the index, JSON, UTF-8, exactly indexLength bytes
12+indexLength  …   the MP3 files, concatenated in ayah order, unmodified
```

The index:

```json
{"reciter":"ar.alafasy","surah":2,"kbps":64,
 "ayahs":[{"n":1,"off":0,"len":31872},{"n":2,"off":31872,"len":18240}]}
```

* `n` is the ayah number within the surah, 1..count, always in order and never sparse.
* `off` is the byte offset of that ayah's MP3 **relative to `dataStart = 12 + indexLength`**.
* `len` is that MP3's exact file size.

So ayah *n* is the byte range `[dataStart + off, dataStart + off + len)` of the container,
and that range is a complete, standalone MP3 file that any decoder will play.

Reading one is a few lines on either platform: read 12 bytes, read `indexLength` bytes of
JSON, then slice. Because the index sits at the front, an app that has received only the
first few KB of a download already knows every ayah boundary and can start playing ayah 1
while the rest of the file is still arriving. Downloads are one HTTP request per surah and
resume with `Range`.

File name: `<reciter id>-<surah, zero-padded to 3>.taqa`, e.g. `ar.alafasy-002.taqa`.

**Verify before use.** `manifest.json` carries the SHA-256 of every container.

---

## `manifest.json`

```json
{"schema":1,
 "generated":"2026-09-12T00:00:00Z",
 "base":"https://github.com/MohamedAbulgasem/Taqwa-data/releases/download/",
 "reciters":[
   {"id":"ar.alafasy","nameEn":"Mishary Rashid Alafasy","nameAr":"مشاري راشد العفاسي",
    "style":"murattal","kbps":64,"gapMs":300,"hue":"amber","photo":null,
    "release":"audio-ar.alafasy-v1","totalBytes":123456789,
    "surahs":[{"n":1,"bytes":12345,"sha256":"…"}]}
 ]}
```

The download URL for a surah is

```
base + release + "/" + "<id>-<nnn>.taqa"
```

* `kbps` — the measured bitrate, for display and for sizing a download.
* `gapMs` — the silence the player must insert between consecutive ayahs. Not cosmetic:
  several of these reciters' files begin at full voice on sample zero, so back-to-back
  playback sounds clipped and rushed without it. Others carry their own padding and want
  a near-zero gap.
* `hue` — which monogram colour the picker uses for this reciter.
* `photo` — always `null` today. Free, defensibly-licensed portraits do not exist for most
  of these reciters, so Taqwa draws a calligraphic monogram instead. The field is here so a
  reciter's foundation can grant one later without an app update.

The app ships a copy of this file so the picker works before the first network call, and
refreshes it from here at most daily.

---

## Licence and credit

The recitations are redistributed under the Islamic Network terms,
**<https://alquran.cloud/terms-and-conditions> §IV**:

> Recitations are licensed to us by the reciters or their estates for free, non-commercial
> redistribution at the bitrates we publish. You may stream, embed and download them for
> personal and educational use. You may bundle them into a commercial product, but please
> note that copyrights lie with the reciters and they may ask you to remove the con[t]ent.

§III of the same page asks downstream users to "cache aggressively at your own edge" and
invites anyone running a full-corpus mirror to get in touch. This repository is such a
mirror, for a free and ad-free app.

**Copyright in each recitation remains with the reciter or their estate.** No claim of
ownership is made here over the audio; the only original work in this repository is the
container format, the manifest and the pipeline, which are covered by the Taqwa
repository's licence.

Credit shown in the app:

> Recitations sourced from the Islamic Network media CDN (cdn.islamic.network), part of the
> Al Quran Cloud project. Copyright in each recitation remains with the reciter or their
> estate.

### Withdrawing a reciter

Any reciter, estate, or the Islamic Network may ask for a recitation to be taken down, and
it will be, without argument. The design makes that a five-minute job with no app update:

1. Delete that reciter's entry from `reciters` in `manifest.json` and commit. Every app
   refreshes the manifest at least daily and the reciter disappears from the picker;
   already-downloaded copies are deleted on the next refresh.
2. `gh release delete audio-<id>-v1 --repo MohamedAbulgasem/Taqwa-data --cleanup-tag`,
   which removes all 114 assets. No other reciter is touched, because no release shares
   assets with another.

To reach us: open an issue on this repository, or use the contact address in the Taqwa
repository.

---

## The pipeline

`tools/`, Python 3 with `ffmpeg`/`ffprobe` and `gh`. The same scripts live in the app
repository at `tools/quran-audio/`. Per reciter:

```sh
python3 tools/fetch.py  ar.alafasy 8            # 6,236 files, 8 workers, resumable
python3 tools/verify.py ar.alafasy              # ffprobe every file; delete and re-fetch bad ones
python3 tools/repair.py ar.alafasy 3 --fallback # persistent 502s, everyayah fallback
python3 tools/pack.py   ar.alafasy              # 114 .taqa containers + SHA-256 + preview clip
python3 tools/check_container.py ar.alafasy     # read the containers back and compare bytes
python3 tools/check_previews.py ar.alafasy      # preview parses and is the right length
python3 tools/publish.py ar.alafasy             # release create + upload + verify 114 assets
python3 tools/manifest.py manifest.json         # rebuild from what is actually published
```

or, for the whole run without supervision:

```sh
python3 tools/watch.py     # finish.py each reciter as its download completes, one at a time
python3 tools/status.py    # where everything is right now
```

`finish.py` chains verify → repair → verify → pack → checks → publish for one reciter and
then calls `finalize.py`, which rewrites `manifest.json`, copies the preview clips into the
app, and commits the manifest here. So the repository is consistent after every reciter
rather than only at the end.

Guarantees the pipeline enforces:

* every ayah is fetched, and re-fetched until ffprobe parses it, finds an audio stream and
  reports a duration over 0.3 s;
* a reciter with a hole is **not shipped** — `manifest.py` includes a reciter only when its
  release has been verified asset by asset;
* the MP3 bytes inside a container are identical to the bytes served by the CDN, checked by
  re-reading the packed container and comparing every slice;
* after upload, `gh release view --json assets` is compared against the packed sizes, so a
  truncated or missing asset fails loudly;
* an asset already uploaded with the right size is never uploaded twice, so an interrupted
  run resumes cheaply.
