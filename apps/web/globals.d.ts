// Type shim for global CSS side-effect imports (e.g. `import './globals.css'`).
// next build auto-generates next-env.d.ts which normally provides this; this file
// makes a standalone `tsc --noEmit` pass too, independent of that generated file.
declare module '*.css';
