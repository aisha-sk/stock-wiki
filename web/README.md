# web

Next.js dashboard (App Router, TypeScript, Tailwind). Lane: SWE.
Every number on screen comes from the API; shapes are in `../docs/CONTRACT.md`.

```bash
npm install
npm run dev
```

Opens on http://localhost:3000 and expects the API on http://localhost:8000. To point it
elsewhere, put `NEXT_PUBLIC_API_URL=...` in `web/.env.local`.

| Path | Role |
|---|---|
| `src/lib/types.ts` | TypeScript mirrors of `../contracts/schemas` |
| `src/lib/api.ts` | Typed fetchers; non-2xx throws `ApiError` with `code` and `message` |
| `src/lib/format.ts` | The one place contract units become display text |
| `src/lib/useApi.ts` | Loading, ready and error states for a fetch, with `reload` |
| `src/lib/useSelectedStock.ts` | The stock chosen with `?symbol=` |
| `src/components/` | Header, stock selector, cards |
| `src/app/` | `/` Dashboard, `/model` Model performance, `/alerts` Alerts |

Checks: `npm run lint`, `npx tsc --noEmit`, `npm run build`.
