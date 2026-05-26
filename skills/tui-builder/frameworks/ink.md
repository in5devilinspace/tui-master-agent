# Ink (TypeScript)

> React, but for the terminal. The default pick for JS/TS shops shipping a CLI with rich interactive output.

- Repo: https://github.com/vadimdemedes/ink
- License: MIT
- Status (May 2026): widely adopted (GitHub Copilot CLI, Gatsby, Cloudflare workers, Prisma all use it)
- Renderer: reconciles a React tree to a flexbox layout via Yoga

## When to choose Ink

Pick Ink when **any one** of these is true:

- The team is a JS/TS shop with React experience already.
- The CLI distributes via npm (`npx mytool`).
- Output is high-information density: tables, spinners, multi-task progress.
- You want JSX-style component composition.

Skip Ink if the target is Termux and you can't afford a Node.js runtime (~60 MB on disk after install).

## Install

```bash
npm init -y
npm install ink react
npm install --save-dev @types/react typescript ts-node
mkdir src && touch src/cli.tsx
```

`tsconfig.json` essentials:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react",
    "esModuleInterop": true,
    "strict": true
  }
}
```

## Hello world

```tsx
// src/cli.tsx
import React from "react";
import { render, Text, Box, useApp, useInput } from "ink";

function App() {
  const { exit } = useApp();
  useInput((input) => { if (input === "q") exit(); });
  return (
    <Box flexDirection="column" alignItems="center">
      <Text bold>Hello, terminal.</Text>
      <Text dimColor>(press q to quit)</Text>
    </Box>
  );
}

render(<App />);
```

Run with `npx ts-node src/cli.tsx`.

## One production pattern — concurrent tasks with status

Ink shines when you have many parallel things going on and need to show each one's status. The pattern: render a list of tasks, each driven by its own hook.

```tsx
import React, { useEffect, useState } from "react";
import { render, Box, Text, Spacer } from "ink";
import Spinner from "ink-spinner";

type Status = "pending" | "running" | "ok" | "fail";

function Task({ label, work }: { label: string; work: () => Promise<void> }) {
  const [status, setStatus] = useState<Status>("pending");
  useEffect(() => {
    setStatus("running");
    work().then(() => setStatus("ok")).catch(() => setStatus("fail"));
  }, []);
  const icon =
    status === "running" ? <Spinner type="dots" /> :
    status === "ok" ? <Text color="green">✓</Text> :
    status === "fail" ? <Text color="red">✗</Text> :
    <Text color="gray">·</Text>;
  return (
    <Box>
      <Box marginRight={1}>{icon}</Box>
      <Text>{label}</Text>
      <Spacer />
      <Text dimColor>{status}</Text>
    </Box>
  );
}

function App() {
  const tasks = [
    { label: "Resolve dependencies", work: () => sleep(800) },
    { label: "Compile TypeScript",   work: () => sleep(1200) },
    { label: "Run tests",            work: () => sleep(2000) },
  ];
  return (
    <Box flexDirection="column">{tasks.map((t, i) => <Task key={i} {...t} />)}</Box>
  );
}

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));
render(<App />);
```

This is the same shape as a CI status board, but composable. Each task is a React component; state-per-task is local; the parent doesn't reach into children.

## Gotchas

1. **Ink does not support all of React.** Hooks work; refs work; concurrent React features are off. Don't expect Suspense.
2. **`process.stdout` writes outside the render bypass Ink's reconciliation.** A stray `console.log` will tear the output. Route logging through `Static` from `ink` or to stderr.
3. **`useInput` only fires when the app has TTY focus.** In piped contexts (`mytool | head`), input is dead — fall back to flags.
4. **Flexbox layout != CSS flexbox exactly.** Yoga implements the spec but a few quirks exist (e.g., `position: absolute` is unavailable).
5. **CI environments often don't render ANSI.** Wrap interactive UI in `process.stdout.isTTY` guards and provide a `--no-tui` plain-text mode.

## Termux verdict

⚠️ Requires Node.js inside Termux (`pkg install nodejs`). Works but Node + npm pulls ~60 MB. Cold-start is ~300ms. Acceptable for interactive use; over budget for a quick launcher script. See [`../termux/compatibility-matrix.md`](../termux/compatibility-matrix.md).

## Useful primitives

- `<Text>`, `<Box>` — the only two layout primitives you need 80% of the time
- `useInput`, `useApp`, `useStdout` — input + lifecycle hooks
- `<Static>` — for log lines that should not re-render
- `ink-spinner`, `ink-select-input`, `ink-text-input` — common widgets
