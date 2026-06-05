# Snap Store media

Source scripts and rendered artefacts for the snapcraft.io/borescope
listing's screenshots and video. Reproduce these any time the CLI
output changes substantially (new flag, renamed column, redesigned
table).

## What's here

`demos/store/` holds the captured `.cast` files, rendered GIFs/MP4s,
and PNG stills for four scenes plus a single concatenated video.

| Scene | Script                          | What it shows                                                   |
|-------|---------------------------------|-----------------------------------------------------------------|
| 1     | `scene1-install.sh`             | `snap install` → `snap connect` → `--version` → `--command services` |
| 2     | `scene2-shellless.sh`           | `juju ssh --container=workload` fails on distroless → `borescope` works |
| 3     | `scene3-repl.sh`                | REPL session: `services`, `checks`, `ls /usr/local/bin`         |
| 4     | `scene4-snapshot.sh`            | `borescope <unit> --snapshot \| jq .` JSON dump                  |

Per-scene outputs (replace `N` with the scene number):

- `sceneN.cast` — raw asciinema recording (replayable, editable).
- `sceneN.gif` — agg-rendered GIF for quick previews.
- `sceneN.mp4` — same content as MP4 (smaller, more compatible).
- `sceneN-final.png` — final frame of the scene as a 1214×730 PNG.
  These are the Snap Store screenshots.

Combined video: `borescope-demo.mp4` (~54s, scenes 1→2→3→4
back-to-back).

## Snap Store upload

The listing accepts up to 5 screenshots (PNG/JPG, 1920×1080 max) and
one video URL (YouTube/Vimeo).

- **Screenshots** — upload `scene{1,2,3,4}-final.png` directly. The
  1214×730 size sits well inside the Snap Store's accepted range.
- **Video** — upload `borescope-demo.mp4` to YouTube as an unlisted
  video and paste the URL into the listing.

## Reproducing the recordings

The recordings were captured in a multipass VM (`cascade`) that already
hosts a Juju 4 controller bootstrapped from a custom build with Pebble
v1.31.0 baked into the agent (borescope needs Pebble ≥ 1.31). The
recording session below assumes that VM and the `bareshell` test charm
are already deployed and active — see [`tests/spread/`](../tests/spread/)
for similar setup recipes, or [`tests/charms/bareshell-test/README.md`](../tests/charms/bareshell-test/README.md).

### One-time setup in the recording VM

```sh
sudo concierge prepare -p k8s            # canonical Juju setup path
# Bootstrap a juju 4 controller with Pebble ≥ 1.31 (see notes below)
juju add-model shimmer-test
cd tests/charms/bareshell-test
make
juju deploy ./bareshell-test_amd64.charm bareshell \
    --resource workload-image=gcr.io/distroless/base-debian12:latest
# Wait for `juju status` to show bareshell/0 active.

sudo snap install borescope                              # the snap under test
sudo snap connect borescope:juju-client-observe          # see #31 to drop this
sudo snap connect borescope:ssh-keys
sudo snap install asciinema --classic
curl -sSL https://github.com/asciinema/agg/releases/download/v1.4.3/agg-x86_64-unknown-linux-gnu \
    -o /tmp/agg && chmod +x /tmp/agg && sudo mv /tmp/agg /usr/local/bin/agg
sudo apt install -y ffmpeg
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
# Re-record any scene:
asciinema rec --overwrite --cols 110 --rows 28 \
    --command "bash scene1-install.sh" scene1.cast
# Render:
agg --font-size 18 --theme monokai scene1.cast scene1.gif
ffmpeg -y -i scene1.gif \
    -movflags faststart -pix_fmt yuv420p \
    -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
    scene1.mp4
# Grab a still ~0.5s before the end:
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 scene1.mp4)
t=$(awk -v d="$dur" 'BEGIN { print (d>1) ? d-0.5 : d/2 }')
ffmpeg -y -ss "$t" -i scene1.mp4 -frames:v 1 scene1-final.png

# Concatenate all four into the listing video:
printf 'file scene1.mp4\nfile scene2.mp4\nfile scene3.mp4\nfile scene4.mp4\n' > concat.txt
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy borescope-demo.mp4
```

The scene scripts call into `_lib.sh` for a tiny `say`/`run` typing
animation (~20ms per character). Adjust the sleep cadence there if a
re-record feels too rushed or sluggish.
