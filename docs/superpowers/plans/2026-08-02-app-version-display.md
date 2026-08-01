# 앱 버전 표시와 릴리스 산출물 정리 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 프로그램 제목 옆에 `YYYYMMDD_HHmmss` 빌드 버전을 보여주고, 빌드마다 `releases/`를 비운 뒤 고정 이름으로 다시 채운다.

**Architecture:** `build_exe.ps1`이 빌드 시각을 한 번만 잡아 VERSION.txt와 프론트엔드 번들에 같은 순간을 넘긴다. Vite `define`이 ISO 문자열을 번들에 박고, 포맷팅은 테스트 가능한 프론트엔드 순수 함수에서 한다.

**Tech Stack:** React 19 + TypeScript + Vite 7 + Tailwind, PowerShell, PyInstaller

## Global Constraints

- 스펙 원본: `docs/superpowers/specs/2026-08-02-app-version-display-design.md`
- 버전 형식은 **`YYYYMMDD_HHmmss`** 고정. 구분자는 언더스코어 하나, 앞자리는 zero-padding.
- 프론트엔드 테스트: `node frontend/scripts/test_frontend_format.mjs` (저장소 루트에서)
- 프론트엔드 빌드: `cd frontend; npm.cmd run build`
- 백엔드는 이 작업에서 건드리지 않는다. `backend/app/main.py`의 `version="0.1.0"`도 그대로 둔다.
- `package.json`의 `"version": "0.1.0"`도 그대로 둔다. 빌드 타임스탬프와 목적이 다르다.
- `releases/`는 이미 `.gitignore` 대상이다. 새로 추가하지 않는다.
- `build_exe.ps1`은 자동 테스트하지 않는다. PyInstaller 실행이 수 분 걸린다.

## 파일 구조

**신규**

| 파일 | 책임 |
|---|---|
| `frontend/src/lib/appVersion.ts` | 타임스탬프 포맷 순수 함수와 `appVersion` 상수 |

**수정**

| 파일 | 변경 |
|---|---|
| `frontend/src/vite-env.d.ts` | `__APP_BUILD_ISO__` 전역 선언 |
| `frontend/vite.config.js` | `define`으로 빌드 시각 주입 |
| `frontend/src/App.tsx` | 헤더 제목 옆에 버전 배지 |
| `frontend/scripts/test_frontend_format.mjs` | 신규 검증 추가 |
| `scripts/build_exe.ps1` | `releases/`로 산출물 이동, 매 빌드 초기화, VERSION.txt 생성 |

---

### Task 1: 버전 포맷 순수 함수와 빌드 시각 주입

**Files:**
- Create: `frontend/src/lib/appVersion.ts`
- Modify: `frontend/src/vite-env.d.ts`
- Modify: `frontend/vite.config.js`
- Modify: `frontend/scripts/test_frontend_format.mjs`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `formatVersionTimestamp(date: Date): string` — 로컬 시각 기준 `YYYYMMDD_HHmmss`
  - `appVersion: string` — 번들에 박힌 빌드 시각을 포맷한 상수
  - 전역 `__APP_BUILD_ISO__: string` — Vite `define`이 주입하는 ISO 8601 문자열
  - 환경변수 `FOSIM_BUILD_ISO` — 설정되어 있으면 그 값을 쓰고, 없으면 설정 로드 시각

`formatVersionTimestamp`는 `Date`를 받는다. 문자열을 받게 만들면 파싱 실패 처리가 함수 안으로 들어와 순수하지 않게 된다. 파싱은 호출부에서 한 번만 한다.

`getMonth()`는 0부터 시작하므로 `+1`을 잊으면 한 달 어긋난 버전이 나간다. 테스트가 8월(`month=7`)을 쓰는 이유다.

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/scripts/test_frontend_format.mjs`의 import 블록 맨 아래(`sidePanelTabs` import 다음 줄)에 추가한다:

```javascript
import { formatVersionTimestamp } from "../src/lib/appVersion.ts";
```

`console.log(...)` 줄 **바로 위**에 추가한다:

```javascript
// getMonth()는 0부터 시작한다. 8월은 month=7이다.
assert.equal(formatVersionTimestamp(new Date(2026, 7, 2, 14, 30, 12)), "20260802_143012");
// 한 자리 수는 모두 zero-padding한다.
assert.equal(formatVersionTimestamp(new Date(2026, 0, 5, 9, 8, 7)), "20260105_090807");
// 자정과 연말 경계.
assert.equal(formatVersionTimestamp(new Date(2026, 11, 31, 0, 0, 0)), "20261231_000000");
assert.equal(formatVersionTimestamp(new Date(2026, 11, 31, 23, 59, 59)), "20261231_235959");
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `node frontend/scripts/test_frontend_format.mjs`
Expected: FAIL — `ERR_MODULE_NOT_FOUND: ../src/lib/appVersion.ts`

- [ ] **Step 3: 순수 함수 구현**

`frontend/src/lib/appVersion.ts`를 새로 만든다.

```typescript
function pad(value: number, width: number): string {
  return String(value).padStart(width, "0");
}

/** 로컬 시각을 YYYYMMDD_HHmmss로 만든다. 릴리스 VERSION.txt와 같은 형식이다. */
export function formatVersionTimestamp(date: Date): string {
  const ymd =
    pad(date.getFullYear(), 4) + pad(date.getMonth() + 1, 2) + pad(date.getDate(), 2);
  const hms =
    pad(date.getHours(), 2) + pad(date.getMinutes(), 2) + pad(date.getSeconds(), 2);
  return `${ymd}_${hms}`;
}

// Vite define은 텍스트 치환이므로 번들에서는 typeof가 "string"으로 접힌다.
// 테스트 러너(Node)에는 이 전역이 없다. typeof는 선언되지 않은 이름에도 던지지 않으므로
// 여기서 현재 시각으로 대체된다. 직접 참조하면 ReferenceError가 난다.
const buildIso =
  typeof __APP_BUILD_ISO__ === "string" ? __APP_BUILD_ISO__ : new Date().toISOString();

/** 이 번들이 만들어진 시각. Vite define이 __APP_BUILD_ISO__를 박아 넣는다. */
export const appVersion = formatVersionTimestamp(new Date(buildIso));
```

- [ ] **Step 4: 전역 타입 선언 추가**

`frontend/src/vite-env.d.ts`를 아래 내용으로 바꾼다:

```typescript
/// <reference types="vite/client" />

/** Vite define이 주입하는 빌드 시각(ISO 8601). vite.config.js 참고. */
declare const __APP_BUILD_ISO__: string;
```

- [ ] **Step 5: Vite define 추가**

`frontend/vite.config.js`를 아래 내용으로 바꾼다. `server` 블록은 그대로 둔다.

```javascript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// build_exe.ps1이 VERSION.txt와 같은 순간을 넘겨준다. 없으면(개발 서버, 수동 빌드)
// 설정을 읽는 시각을 쓴다.
const buildIso = process.env.FOSIM_BUILD_ISO ?? new Date().toISOString();

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_BUILD_ISO__: JSON.stringify(buildIso),
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `node frontend/scripts/test_frontend_format.mjs`
Expected: PASS

Run: `cd frontend; npm.cmd run build`
Expected: 타입 체크와 번들 생성 통과

테스트 러너는 `appVersion.ts`를 import하므로 모듈 최상단의 `appVersion` 상수도 평가된다. Step 3의 `typeof` 가드가 이것을 통과시킨다. `ReferenceError: __APP_BUILD_ISO__ is not defined`가 보이면 가드를 빠뜨린 것이다.

번들에 실제로 박혔는지 확인한다:

```bash
grep -o "__APP_BUILD_ISO__" frontend/dist/assets/*.js
```
Expected: 출력 없음 (치환되었으므로 원본 식별자가 남지 않는다)

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/lib/appVersion.ts frontend/src/vite-env.d.ts frontend/vite.config.js frontend/scripts/test_frontend_format.mjs
git commit -m "feat: inject build timestamp into frontend bundle"
```

---

### Task 2: 헤더에 버전 표시

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/scripts/test_frontend_format.mjs`

**Interfaces:**
- Consumes: Task 1의 `appVersion`
- Produces: 없음

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/scripts/test_frontend_format.mjs`의 단언 블록에서 `assert.match(appSource, /SidePanelTabs/);` **바로 아래**에 추가한다:

```javascript
assert.match(appSource, /appVersion/);
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `node frontend/scripts/test_frontend_format.mjs`
Expected: FAIL — `The input did not match the regular expression /appVersion/`

- [ ] **Step 3: 구현**

`frontend/src/App.tsx`의 import 블록에서 `import { confidenceTone } from "./lib/format";` **바로 위**에 추가한다:

```tsx
import { appVersion } from "./lib/appVersion";
```

헤더의 제목 줄을 찾는다:

```tsx
            <div className="flex min-w-0 items-baseline gap-3">
              <h1 className="shrink-0 text-base font-semibold text-graphite">
                Fastening parameter optimizer
              </h1>
              <p className="truncate text-xs text-steel">{cycleSummary}</p>
            </div>
```

`<h1>`과 `<p>` 사이에 한 줄 넣는다. 나머지는 건드리지 않는다:

```tsx
              <span className="shrink-0 font-mono text-[11px] text-slate-400">{appVersion}</span>
```

`shrink-0`을 주는 이유는 사이클 요약이 길어져도 타임스탬프가 잘리지 않게 하기 위해서다. 잘린 타임스탬프는 버전 식별에 쓸모가 없다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `node frontend/scripts/test_frontend_format.mjs`
Expected: PASS

Run: `cd frontend; npm.cmd run build`
Expected: 통과

- [ ] **Step 5: 실제 화면 확인**

Run: `cd frontend; npm.cmd run dev` 후 브라우저에서 `http://127.0.0.1:5173/`

제목 "Fastening parameter optimizer" 오른쪽에 `20260802_143012` 같은 회색 고정폭 문자열이 보이고, 그 오른쪽에 사이클 요약이 이어지는지 확인한다.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/App.tsx frontend/scripts/test_frontend_format.mjs
git commit -m "feat: show build version next to app title"
```

---

### Task 3: 릴리스 산출물을 releases/로 통합

**Files:**
- Modify: `scripts/build_exe.ps1`

**Interfaces:**
- Consumes: Task 1의 `FOSIM_BUILD_ISO` 환경변수 규약
- Produces: `releases/FOSIM/`, `releases/FOSIM-exe.zip`, `releases/VERSION.txt`

기존 스크립트는 저장소 밖 `..\..\outputs`에 `Resolve-Path`를 걸어 그 폴더가 없으면 시작하자마자 실패한다. 이 태스크가 그 경로를 없앤다.

`$env:FOSIM_BUILD_ISO`는 프론트엔드 빌드 **전에** 설정해야 한다. Vite는 설정 파일을 읽을 때 한 번만 평가한다.

- [ ] **Step 1: 구현**

`scripts/build_exe.ps1` 전체를 아래로 바꾼다.

```powershell
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$BackendRoot = Join-Path $ProjectRoot "backend"
$ReleasesRoot = Join-Path $ProjectRoot "releases"
$AppName = "FOSIM"

# 빌드 시각은 여기서 한 번만 잡는다. VERSION.txt와 프론트엔드 번들이 같은 값을 쓴다.
$Now = Get-Date
$Version = $Now.ToString("yyyyMMdd_HHmmss")
$env:FOSIM_BUILD_ISO = $Now.ToString("o")

# 매 빌드마다 releases/를 비운다. 버전별 zip을 쌓지 않고 항상 최신 하나만 둔다.
if (Test-Path $ReleasesRoot) { Remove-Item -LiteralPath $ReleasesRoot -Recurse -Force }
New-Item -ItemType Directory -Path $ReleasesRoot | Out-Null

Set-Location $FrontendRoot
npm.cmd install
npm.cmd test
npm.cmd run build

Set-Location $BackendRoot
python -m pytest -q

$DistPath = Join-Path $ProjectRoot "frontend\dist"
$SamplePath = Join-Path $ProjectRoot "sample-data"
$DocsPath = Join-Path $ProjectRoot "docs"

if (Test-Path "dist") { Remove-Item -LiteralPath "dist" -Recurse -Force }
if (Test-Path "build") { Remove-Item -LiteralPath "build" -Recurse -Force }

python -m PyInstaller `
  --noconfirm `
  --clean `
  --name $AppName `
  --add-data "$DistPath;frontend/dist" `
  --add-data "$SamplePath;sample-data" `
  --add-data "$DocsPath;docs" `
  desktop_launcher.py

$BuildSource = Join-Path $BackendRoot "dist\$AppName"
$ReleaseApp = Join-Path $ReleasesRoot $AppName
$ExeZip = Join-Path $ReleasesRoot "$AppName-exe.zip"
$VersionFile = Join-Path $ReleasesRoot "VERSION.txt"

Copy-Item -LiteralPath $BuildSource -Destination $ReleaseApp -Recurse

$ReadmePath = Join-Path $ReleaseApp "README_RUN.txt"
@"
FOSIM.exe Run Guide

FOSIM = Fastening Optimization & Simulation Manager
Version: $Version

1. Extract the whole zip file to a folder.
2. Run FOSIM.exe.
3. The browser opens automatically.
4. Close the console window to stop the app.

Notes:
- This MVP uses CSV/sample data only.
- Actual SH-2 communication and device write are not included.
- If Windows shows a security warning, choose More info, then Run anyway.
"@ | Set-Content -Path $ReadmePath -Encoding UTF8

Compress-Archive -Path $ReleaseApp -DestinationPath $ExeZip -Force

@"
$AppName
Version: $Version
Format: YYYYMMDD_HHmmss
Build source: $BuildSource
Package: $ExeZip
Created: $($Now.ToString("yyyy-MM-dd HH:mm:ss"))
"@ | Set-Content -Path $VersionFile -Encoding UTF8

Write-Host "Created $ExeZip (version $Version)"
```

- [ ] **Step 2: 문법 확인**

PyInstaller 전체 실행은 수 분 걸리므로 먼저 파싱만 검사한다.

Run:
```powershell
$null = [System.Management.Automation.PSParser]::Tokenize((Get-Content -Raw scripts/build_exe.ps1), [ref]$null); "parsed"
```
Expected: `parsed` 출력, 오류 없음

- [ ] **Step 3: 실제 빌드 1회**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1`

확인한다:
- `releases/`에 `FOSIM/`, `FOSIM-exe.zip`, `VERSION.txt` 셋만 있다
- 기존 `releases/FOSIM_20260726_124309` 폴더가 사라졌다
- `releases/VERSION.txt`의 `Version:` 값과 `FOSIM.exe`를 실행해 열린 화면 헤더의 버전이 같다

빌드가 오래 걸리거나 PyInstaller 환경이 준비되지 않았다면 이 스텝은 사용자에게 넘기고 커밋은 진행한다. 스크립트 변경은 Step 2의 파싱 검사로 최소 보증된다.

- [ ] **Step 4: 커밋**

```bash
git add scripts/build_exe.ps1
git commit -m "build: write release artifacts to releases/ with a single fixed name"
```

---

## 자체 검토 결과

**스펙 커버리지**

| 스펙 절 | 담당 태스크 |
|---|---|
| 1. 버전 값의 단일 출처 (Now 1회 계산, define, appVersion.ts, vite-env.d.ts) | Task 1, Task 3 Step 1 |
| 2. 화면 표시 (h1 뒤, mono, shrink-0, dev 접미사 없음) | Task 2 |
| 3. 빌드 산출물 (releases/ 이동, 매 빌드 초기화, 고정 이름 3개, VERSION.txt 형식) | Task 3 |
| 4. 테스트 (순수 함수 단위, zero-padding, App.tsx 정규식) | Task 1 Step 1, Task 2 Step 1 |
| 범위 밖 (semver, git 해시) | 어느 태스크도 건드리지 않음 — Global Constraints에 명시 |

**타입 일관성**

Task 1이 내보내는 `formatVersionTimestamp(date: Date): string`과 `appVersion: string`을 Task 2가 그대로 쓴다. Task 1이 정한 환경변수 이름 `FOSIM_BUILD_ISO`를 Task 3이 같은 철자로 설정하고, Task 1의 `vite.config.js`가 같은 철자로 읽는다. 전역 이름 `__APP_BUILD_ISO__`는 `vite-env.d.ts` 선언, `vite.config.js`의 `define` 키, `appVersion.ts`의 참조 세 곳에서 일치한다.

**의존 순서**

Task 1 → Task 2는 필수 순서다. Task 3은 Task 1의 환경변수 규약에만 의존하므로 Task 2와 순서를 바꿔도 되지만, 실제 빌드 검증이 헤더 표시를 확인하므로 마지막에 둔다.
