# Snap Store media

Source scripts and rendered artefacts for the snapcraft.io/borescope
listing's screenshots and video. Reproduce these any time the CLI
output changes substantially (new flag, renamed column, redesigned
table).

## What's here

`demos/store/` holds the captured `.cast` files, rendered GIFs/MP4s,
and PNG stills for five scenes plus a single concatenated video.

| Scene | Script                          | Rows | What it shows                                                                  |
|-------|---------------------------------|------|--------------------------------------------------------------------------------|
| 1     | `scene1-install.sh`             | 28   | `snap install` → `snap connect` → `--version` → `--command services`           |
| 2     | `scene2-shellless.sh`           | 28   | `juju ssh --container=workload` fails on distroless → `borescope` works         |
| 3     | `scene3-repl.sh`                | 28   | Real REPL session driven by `expect`: `services`, `checks`, `ls /usr/local/bin` |
| 4     | `scene4-snapshot.sh`            | 80   | `borescope <unit> --snapshot \| jq .` JSON dump (first 75 lines)                |
| 5     | `scene5-here.sh`                | 30   | `juju ssh <unit> 'borescope --here --container redis/snappass …'`              |

Per-scene outputs (replace `N` with the scene number):

- `sceneN.cast` — raw asciinema recording (replayable, editable).
- `sceneN.mp4` — full-resolution H.264 for the listing video.
- `sceneN.gif` — Snap-Store-compliant GIF: 1214 wide, ≤16.7 fps,
  ≤627 KB, ≤28 s, aspect ratio between 1:2 and 2:1.
- `sceneN-final.png` — final frame as PNG (1214×730 for scenes 1–3,
  1214×780 for scene 5, 1214×2040 for scene 4 — the snapshot needs
  the height).

Combined video: `borescope-demo.mp4` (~76 s, scenes 1 → 2 → 3 → 4 → 5
back-to-back on a 1214×2040 canvas anchored top-left, padded with
monokai background `#26271f`). Scene 4's last frame is held an extra
six seconds (`tpad=stop_duration=6:stop_mode=clone`) so the JSON is
readable. The video does **not** need to follow the GIF rules — only
the standalone `sceneN.gif` files do.

## Snap Store upload

The listing accepts up to 5 screenshots and one video URL
(YouTube/Vimeo).

- **Screenshots** — upload `scene{1,2,3,4,5}-final.png` (PNG) **or**
  `scene{1,2,3,4,5}.gif` (animated). The PNGs work fine if the GIFs
  are rejected for some reason; otherwise the GIFs are punchier.
- **Video** — upload `borescope-demo.mp4` to YouTube as an unlisted
  video and paste the URL into the listing.

The Snap Store enforces these rules on GIF screenshots (the rules
the PNGs and the linked video are exempt from):

- Resolution: min 480×480, max 3840×2160.
- Aspect ratio: between 1:2 (tall) and 2:1 (wide).
- File size: ≤2 MB per GIF.
- Length: ≤40 s.
- Frame rate: 1–30 fps.

`scene{1,2,3,5}.gif` are 1214×730–780 (≈ 1.55–1.66 : 1);
`scene4.gif` is 1214×2040 (≈ 1 : 1.68) — the snapshot needs the
height. All are well inside the rules.

## Reproducing the recordings

The recordings were captured in a multipass VM (`cascade`) that already
hosts a Juju 4 controller bootstrapped from a custom build with Pebble
v1.31.0 baked into the agent (borescope needs Pebble ≥ 1.31). The
recording session below assumes that VM and the `bareshell-test` +
`snappass-test` charms are already deployed and active — see
[`tests/spread/`](../tests/spread/) for similar setup recipes, or
[`tests/charms/bareshell-test/README.md`](../tests/charms/bareshell-test/README.md).

### One-time setup in the recording VM

```sh
sudo concierge prepare -p k8s            # canonical Juju setup path
# Bootstrap a juju 4 controller with Pebble ≥ 1.31 (see notes below)
juju add-model shimmer-test
cd tests/charms/bareshell-test
make
juju deploy ./bareshell-test_amd64.charm bareshell \
    --resource workload-image=gcr.io/distroless/base-debian12:latest
juju deploy snappass-test --channel=latest/stable
# Wait for `juju status` to show both units active.

sudo snap install borescope                              # the snap under test
sudo snap connect borescope:juju-client-observe          # see #31 to drop these
sudo snap connect borescope:ssh-keys
sudo snap install asciinema --classic
sudo apt install -y expect ffmpeg
curl -sSL https://github.com/asciinema/agg/releases/download/v1.4.3/agg-x86_64-unknown-linux-gnu \
    -o /tmp/agg && chmod +x /tmp/agg && sudo mv /tmp/agg /usr/local/bin/agg
```

### Scene 5 needs borescope *inside* the charm container

`--here` mode talks to the workload's Pebble socket directly through
the charm container's mount at `/charm/containers/<name>/pebble.socket`,
which means the `borescope` binary has to live inside that container.
The snap is workstation-only — k8s pods don't run snapd — so install
via uv against the wheel:

```sh
# On the host: build the wheel and copy it in.
uv build
juju scp dist/borescope-1.0.2-py3-none-any.whl snappass-test/0:/tmp/

# Inside snappass-test/0 (via juju ssh): install uv, then the wheel.
juju ssh snappass-test/0 'curl -LsSf https://astral.sh/uv/install.sh | sh'
juju ssh snappass-test/0 '~/.local/bin/uv tool install /tmp/borescope-1.0.2-py3-none-any.whl'
# borescope is now at /root/.local/bin/borescope inside snappass-test/0.
```

### Pebble ≥ 1.31 caveat

Borescope 1.0 needs the workload's Pebble to be ≥ 1.31.0 so it can
read `--format=json`. Stock juju 3.6.x / 4.0.x snaps still ship Pebble
1.26 inside `containeragent`. Until a juju snap ships 1.31, the
recording VM has to use a custom juju build (in our case
`/home/ubuntu/juju-build/`) that has Pebble 1.31 vendored into the
agent. The `snapshot` scene in particular exposes the Pebble version
under `system.version`, so a future re-record will need to update the
expected value.

### Record + render

```sh
cd demos/store
export TERM=xterm-256color
# Re-record any scene (scene 4 needs --rows 80 for the JSON, scene 5
# needs --rows 30, all others 28):
asciinema rec --overwrite --cols 110 --rows 28 \
    --command "bash scene1-install.sh" scene1.cast

# Render the full-resolution MP4 from the cast via agg:
agg --font-size 18 --theme monokai scene1.cast scene1-fullres.gif
ffmpeg -y -i scene1-fullres.gif \
    -movflags faststart -pix_fmt yuv420p \
    -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
    scene1.mp4
rm scene1-fullres.gif

# Render the store-compliant GIF (native 1214 wide, 15 fps,
# palette-optimised). Stays well under the 2 MB per-file ceiling.
ffmpeg -y -i scene1.mp4 -vf \
    "fps=15,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer:bayer_scale=4" \
    scene1.gif

# Grab a still ~0.5s before the end:
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 scene1.mp4)
t=$(awk -v d="$dur" 'BEGIN { print (d>1) ? d-0.5 : d/2 }')
ffmpeg -y -ss "$t" -i scene1.mp4 -frames:v 1 scene1-final.png

# Concatenate all five scenes into the listing video. Pad every scene
# to a uniform 1214×2040 canvas anchored top-left (scene 4 is already
# 2040 tall; everything else gets monokai bg below). Scene 4 also
# gets a 6-second freeze at the end so the JSON is readable. Then
# concat with -c copy, which works cleanly now that codec params
# match across inputs.
for s in 1 2 3 5; do
    ffmpeg -y -i scene${s}.mp4 \
        -vf "pad=1214:2040:0:0:0x26271f,setsar=1" \
        -c:v libx264 -pix_fmt yuv420p -r 30 -movflags faststart \
        scene${s}-canvas.mp4
done
ffmpeg -y -i scene4.mp4 \
    -vf "tpad=stop_duration=6:stop_mode=clone,setsar=1" \
    -c:v libx264 -pix_fmt yuv420p -r 30 -movflags faststart \
    scene4-canvas.mp4
printf 'file scene1-canvas.mp4\nfile scene2-canvas.mp4\nfile scene3-canvas.mp4\nfile scene4-canvas.mp4\nfile scene5-canvas.mp4\n' > concat.txt
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy borescope-demo.mp4
```

The scene scripts call into `_lib.sh` for a tiny `say`/`run` typing
animation (~20-40ms per character). Scene 3 uses `expect` to drive a
real REPL so the `pebble:/#` prompts, typed commands, and `exit` all
flow through a real tty. Adjust sleep cadence in either place if a
re-record feels too rushed or sluggish.
