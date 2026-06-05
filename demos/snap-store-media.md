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
- `sceneN.gif` — agg-rendered GIF for quick previews.
- `sceneN.mp4` — same content as MP4 (smaller, more compatible).
- `sceneN-final.png` — final frame as PNG (1214×730 for scenes 1–3,
  1214×780 for scene 5, 1214×2040 for scene 4 — the snapshot needs the
  height).

Combined video: `borescope-demo.mp4` (~92s, scenes 1 → 2 → 3 → 5
back-to-back, padded to a common 1214×780 canvas). Scene 4 is *not*
in the video — a static JSON dump doesn't reward motion. Use its PNG
in the screenshots slot to convey the same information.

## Snap Store upload

The listing accepts up to 5 screenshots (PNG/JPG, 1920×1080 max) and
one video URL (YouTube/Vimeo).

- **Screenshots** — upload all five `scene{1,2,3,4,5}-final.png`.
- **Video** — upload `borescope-demo.mp4` to YouTube as an unlisted
  video and paste the URL into the listing.

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

# Render to GIF and MP4:
agg --font-size 18 --theme monokai scene1.cast scene1.gif
ffmpeg -y -i scene1.gif \
    -movflags faststart -pix_fmt yuv420p \
    -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
    scene1.mp4

# Grab a still ~0.5s before the end:
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 scene1.mp4)
t=$(awk -v d="$dur" 'BEGIN { print (d>1) ? d-0.5 : d/2 }')
ffmpeg -y -ss "$t" -i scene1.mp4 -frames:v 1 scene1-final.png

# Concatenate scenes 1, 2, 3, 5 into the listing video. They have
# slightly different heights, so pad to 780 first (skipping scene 4 —
# its 2040-row snapshot is for the still only):
for s in 1 2 3 5; do
    ffmpeg -y -i scene${s}.mp4 \
        -vf "pad=1214:780:0:(oh-ih)/2:black" \
        -c:v libx264 -pix_fmt yuv420p -movflags faststart \
        scene${s}-padded.mp4
done
printf 'file scene1-padded.mp4\nfile scene2-padded.mp4\nfile scene3-padded.mp4\nfile scene5-padded.mp4\n' > concat.txt
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy borescope-demo.mp4
```

The scene scripts call into `_lib.sh` for a tiny `say`/`run` typing
animation (~20-40ms per character). Scene 3 uses `expect` to drive a
real REPL so the `pebble:/#` prompts, typed commands, and `exit` all
flow through a real tty. Adjust sleep cadence in either place if a
re-record feels too rushed or sluggish.
