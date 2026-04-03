# GenZLease on GenLayer

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/license/mit/)
[![Discord](https://img.shields.io/badge/Discord-Join%20us-5865F2?logo=discord&logoColor=white)](https://discord.gg/8Jm4v89VAu)
[![Telegram](https://img.shields.io/badge/Telegram--T.svg?style=social&logo=telegram)](https://t.me/genlayer)

An **AI-native RWA leasing protocol** built on **GenLayer Intelligent Contracts**.

This repository started from the GenLayer football-bets starter and now includes a dedicated
**GenZLease** intelligent contract for land/property leasing workflows, plus frontend contract
integration layers and hooks to power leasing-focused dApps.

---

## What this project does

GenZLease is designed for **real-world property leasing** where legal and off-chain verification
must happen before on-chain execution.

### Core goals

- Verify ownership and title metadata (registry/API integrations).
- Manage listing lifecycle (draft, active, paused, rented, disputed).
- Create and manage lease agreements with escrow and dispute handling.
- Provide tenant/landlord profiles and reputation signals.
- Use AI + web access inside intelligent contracts for evidence-driven decisions.

### Why GenLayer

GenLayer allows contracts to:

- Access web resources (`gl.nondet.web.*`).
- Run LLM reasoning (`gl.nondet.exec_prompt`).
- Enforce deterministic consensus with equivalence principles.

That combination makes it suitable for leasing flows where verification and adjudication are not
purely deterministic from on-chain state.

---

## Repository structure

```text
contracts/
  football_bets.py           # Original starter contract
  genzlease.py               # Main RWA leasing intelligent contract

deploy/
  deployScript.ts            # Contract deployment script (currently football_bets target)

test/
  test_footbal_bet.py        # Starter integration tests for football_bets

frontend/
  app/, components/          # Existing football UI (kept for now)
  lib/contracts/
    FootballBets.ts          # Refactored football client wrapper
    GenZLease.ts             # GenZLease client wrapper
    base.ts                  # Shared GenLayer contract base helper
    genzlease-types.ts       # Domain types for GenZLease responses
  lib/hooks/
    useFootballBets.ts
    useGenZLease.ts          # React Query hooks for GenZLease

scripts/
  test_read_functions.py     # Python utility to call all read-only methods by schema
```

---

## Tech stack

- **Intelligent contracts:** Python + GenVM (`genlayer`)
- **Frontend:** Next.js 15/16, React, TypeScript, TanStack Query
- **SDKs:** `genlayer-js` (frontend), `genlayer-py` (Python script)
- **Wallet:** MetaMask + viem helpers

---

## Quick start

## 1) Prerequisites

- Node.js + npm
- Python 3.10+ (3.12+ recommended for latest `genlayer-py`)
- GenLayer CLI installed globally:

```bash
npm install -g genlayer
```

- Access to a GenLayer Studio endpoint (local or hosted)

## 2) Install dependencies

```bash
npm install
cd frontend && npm install
```

## 3) Configure network + contract address

Create `frontend/.env` (or `.env.local`) and set:

```bash
NEXT_PUBLIC_GENLAYER_RPC_URL=https://studio.genlayer.com/api
NEXT_PUBLIC_CONTRACT_ADDRESS=<DEPLOYED_CONTRACT_ADDRESS>
```

> For GenZLease integration, point `NEXT_PUBLIC_CONTRACT_ADDRESS` to the deployed `GenZLease` contract.

## 4) Run frontend

```bash
cd frontend
npm run dev
```

---

## Deploying contracts

Current deploy script still targets `contracts/football_bets.py`.
To deploy GenZLease, either:

- update `deploy/deployScript.ts` target path to `contracts/genzlease.py`, or
- deploy directly with your preferred GenLayer workflow.

Standard deploy flow:

```bash
genlayer network
npm run deploy
```

---

## GenZLease frontend integration

The codebase includes reusable building blocks for leasing flows:

- `frontend/lib/contracts/GenZLease.ts`
  - Read methods: listing, lease, stats, tenant profile, landlord profile, precedent search
  - Write methods: `withdrawFees`, `setPaused`
- `frontend/lib/hooks/useGenZLease.ts`
  - React Query hooks for reads/mutations
- `frontend/lib/contracts/base.ts`
  - Shared contract client helpers (`read`, `write`, tx receipt waiting, tx lookup)

UI wiring is intentionally deferred so product/UX can be redesigned around leasing-specific screens.

---

## Python utility: test all read-only methods

Use the script to fetch a deployed schema and call every readonly method automatically:

```bash
python3 scripts/test_read_functions.py \
  --contract 0x089BAD15ABF412083A51badc891Da97c3583cdA5 \
  --endpoint https://studio.genlayer.com/api \
  --sample-address 0x0000000000000000000000000000000000000000
```

Useful flags:

- `--contract` target contract address
- `--endpoint` RPC URL
- `--sample-address` placeholder for address-like params
- `--raw-return` pass through raw return values

---

## Testing and checks

### Contract tests (starter suite)

```bash
gltest
```

> Existing tests currently cover the football starter contract. Add/extend tests for GenZLease before production.

### Frontend type check

```bash
cd frontend
npx tsc --noEmit
```

---

## Roadmap (recommended)

- [ ] Update deployment script default to `genzlease.py`
- [ ] Add end-to-end tests for GenZLease lifecycle (listing → lease → escrow → dispute)
- [ ] Add per-country registry adapter architecture (AGIS, eCitizen, etc.)
- [ ] Build leasing-native UI flows and admin/operator dashboards
- [ ] Add contract/address separation for multi-contract frontend support

---

## Documentation

- GenLayer docs: <https://docs.genlayer.com/>
- GenLayer intelligent contracts: <https://docs.genlayer.com/developers/intelligent-contracts/introduction>
- Reading data in dApps: <https://docs.genlayer.com/developers/decentralized-applications/reading-data>
- Writing data in dApps: <https://docs.genlayer.com/developers/decentralized-applications/writing-data>
- Querying transactions: <https://docs.genlayer.com/developers/decentralized-applications/querying-a-transaction>

---

## License

MIT — see [LICENSE](LICENSE).
