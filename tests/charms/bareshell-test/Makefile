# Build the bareshell-test charm.
#
#   make           — build everything (workload binary + packed charm)
#   make charm     — same as default
#   make binary    — just build the workload-app binary (placed at src/workload-app
#                    so charmcraft picks it up)
#   make clean     — remove the workload binary and any packed .charm artefact
#
# The Go toolchain is only required for `make binary` (and therefore for
# `make charm`).  `charmcraft pack` itself doesn't need Go — once the binary
# is in src/, packing is a pure Python charm build.

CHARM         ?= bareshell-test_amd64.charm
BINARY        ?= src/workload-app
WORKLOAD_SRC  ?= workload-src

.PHONY: charm
charm: $(CHARM)

$(CHARM): $(BINARY) charmcraft.yaml src/charm.py
	charmcraft clean
	charmcraft pack

.PHONY: binary
binary: $(BINARY)

$(BINARY): $(WORKLOAD_SRC)/main.go $(WORKLOAD_SRC)/go.mod
	cd $(WORKLOAD_SRC) && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
	    go build -trimpath -ldflags='-s -w' -o ../$(BINARY) .

.PHONY: clean
clean:
	rm -f $(BINARY) $(CHARM)
