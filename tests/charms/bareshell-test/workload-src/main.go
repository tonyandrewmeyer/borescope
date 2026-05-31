// workload-app: a tiny static "workload" for the bareshell-test charm.
//
// One binary, two modes (selected by argv[1]):
//
//   workload-app http [addr]    — HTTP server with /health, /metrics, /ready
//   workload-app ticker [N]     — logs a tick line to stdout every N seconds (default 2)
//
// Built static (CGO_ENABLED=0) so it runs in distroless workloads with no shell
// and no libc dependencies the image might not have.
package main

import (
	"fmt"
	"net/http"
	"os"
	"strconv"
	"time"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: workload-app <http|ticker> [args...]")
		os.Exit(2)
	}
	switch os.Args[1] {
	case "http":
		runHTTP()
	case "ticker":
		runTicker()
	default:
		fmt.Fprintf(os.Stderr, "unknown mode: %s\n", os.Args[1])
		os.Exit(2)
	}
}

func runHTTP() {
	addr := ":8080"
	if len(os.Args) >= 3 {
		addr = os.Args[2]
	}
	start := time.Now()
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintln(w, "ok")
	})
	http.HandleFunc("/ready", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintln(w, "ready")
	})
	http.HandleFunc("/metrics", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "uptime_seconds %d\n", int64(time.Since(start).Seconds()))
	})
	fmt.Fprintf(os.Stdout, "http: listening on %s\n", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		fmt.Fprintf(os.Stderr, "http: %v\n", err)
		os.Exit(1)
	}
}

func runTicker() {
	every := 2 * time.Second
	if len(os.Args) >= 3 {
		n, err := strconv.Atoi(os.Args[2])
		if err == nil && n > 0 {
			every = time.Duration(n) * time.Second
		}
	}
	for i := 0; ; i++ {
		fmt.Fprintf(os.Stdout, "tick %d at %s\n", i, time.Now().UTC().Format(time.RFC3339))
		time.Sleep(every)
	}
}
