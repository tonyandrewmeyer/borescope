# borescope documentation

_A natural shell for debugging Juju Kubernetes workload containers, through Pebble, with your existing Juju authority._

<p>
  This documentation follows the
  <a href="https://diataxis.fr/" target="_blank" rel="noopener">Diataxis</a> framework, organising
  content by what you need: learning, solving problems, looking things
  up, or understanding how the system works.
</p>

<h2 id="start-here">Start here</h2>

<ol>
  <li>
    <strong>New to borescope?</strong> Work through the
    <a href="tutorial.html">tutorial</a>. It takes you from install to
    poking around a live container in about ten minutes.
  </li>
  <li>
    <strong>Have a unit in mind?</strong> Jump to
    <a href="howto-connect.html">Connect to a unit</a> to pick the right
    container, model, or controller.
  </li>
  <li>
    <strong>Looking something up?</strong> The
    <a href="reference-cli.html">CLI reference</a> lists every flag, and the
    <a href="reference-commands.html">command reference</a> covers every
    built-in command.
  </li>
  <li>
    <strong>Want to know how it works?</strong> Start with
    <a href="explanation-architecture.html">How borescope works</a> and
    <a href="explanation-transport.html">How it reaches Pebble</a>.
  </li>
</ol>

<section class="doc-section tutorial">
<h2>Tutorial</h2>
<div class="doc-cards">
  <a href="tutorial.html" class="doc-card">
    <h3>Debug your first container</h3>
    <p>
      A guided walkthrough from installation to reading logs, services,
      and the plan on a live workload container. No prior experience
      required.
    </p>
  </a>
</div>
</section>

<section class="doc-section howto">
<h2>How-to guides</h2>
<div class="doc-cards">
  <a href="howto-connect.html" class="doc-card">
    <h3>Connect to a unit</h3>
    <p>
      Target the right workload container, model, and controller, and
      understand what borescope does when you don&rsquo;t say.
    </p>
  </a>
  <a href="howto-here.html" class="doc-card">
    <h3>Run inside the charm container</h3>
    <p>
      Use <code>--here</code> from a charm hook or <code>juju ssh</code>
      session to talk to a mounted Pebble socket directly, or point at
      any socket with <code>--socket</code>.
    </p>
  </a>
  <a href="howto-oneshot.html" class="doc-card">
    <h3>Run one command (no REPL)</h3>
    <p>
      Drive a single command with <code>--command</code>, or pipe a
      script in on stdin, for aliases, CI, and automation.
    </p>
  </a>
  <a href="howto-files.html" class="doc-card">
    <h3>Copy files in and out</h3>
    <p>
      Pull a log or config file out of a shell-less container, or push a
      patched file back in, with <code>pull</code> and <code>push</code>.
    </p>
  </a>
  <a href="howto-snapshot.html" class="doc-card">
    <h3>Capture a state snapshot</h3>
    <p>
      Produce a stable JSON document of services, plan, checks, notices,
      and recent logs, for bug reports and tooling.
    </p>
  </a>
</div>
</section>

<section class="doc-section reference">
<h2>Reference</h2>
<div class="doc-cards">
  <a href="reference-cli.html" class="doc-card">
    <h3>CLI reference</h3>
    <p>Every command-line argument, the modes they select, and exit codes.</p>
  </a>
  <a href="reference-commands.html" class="doc-card">
    <h3>Command reference</h3>
    <p>Every built-in command (shell, files, Pebble-native), plus the <code>exec</code> escape hatch.</p>
  </a>
</div>
</section>

<section class="doc-section explanation">
<h2>Explanation</h2>
<div class="doc-cards">
  <a href="explanation-architecture.html" class="doc-card">
    <h3>How borescope works</h3>
    <p>
      The three layers (transport, discovery, shell) and why the
      separation matters.
    </p>
  </a>
  <a href="explanation-transport.html" class="doc-card">
    <h3>How it reaches Pebble</h3>
    <p>
      Why borescope can debug a shell-less rock, how it goes through the
      charm container, and the two transport backends.
    </p>
  </a>
  <a href="explanation-scope.html" class="doc-card">
    <h3>Scope and philosophy</h3>
    <p>
      Why borescope is Kubernetes-only, ships a minimal command set, and
      leans on <code>exec</code> rather than reimplementing coreutils.
    </p>
  </a>
</div>
</section>
