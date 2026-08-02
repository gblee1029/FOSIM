# 앱 버전 표시와 릴리스 산출물 정리 설계

**목표 1:** 프로그램 제목 옆에 `YYYYMMDD_HHmmss` 형식의 빌드 버전을 보여준다.

**목표 2:** 빌드할 때마다 버전이 붙은 zip을 새로 쌓지 않고, `releases/`를 비운 뒤 고정 이름으로 다시 채운다.

## 배경

`releases/FOSIM_20260726_124309/VERSION.txt`에 이미 `Format: YYYYMMDD_HHmmss` 규약이 있다. 그 폴더를 만든 스크립트는 저장소에 없고, `scripts/build_exe.ps1`은 저장소 밖 `..\..\outputs\FOSIM-exe.zip`으로 떨어뜨린다. 두 경로가 갈라져 있어 "지금 돌고 있는 exe가 어느 빌드인지" 확인할 방법이 화면에 없다.

## 1. 버전 값의 단일 출처

`scripts/build_exe.ps1`이 빌드 시작 시 시각을 한 번만 잡고 두 소비자에게 같은 순간을 넘긴다.

```powershell
$Now = Get-Date
$Version = $Now.ToString("yyyyMMdd_HHmmss")   # VERSION.txt
$env:FOSIM_BUILD_ISO = $Now.ToString("o")     # npm run build
```

`frontend/vite.config.js`가 `define`으로 `__APP_BUILD_ISO__`를 번들에 박는다. 환경변수가 없으면(= `npm run dev`, 개발자가 직접 `npm run build`) 설정 로드 시각으로 대체한다.

```js
define: {
  __APP_BUILD_ISO__: JSON.stringify(process.env.FOSIM_BUILD_ISO ?? new Date().toISOString()),
}
```

포맷팅은 설정 파일이 아니라 프론트엔드 안에서 한다. `vite.config.js`는 테스트가 import할 수 없고, 포맷터를 양쪽에 두면 두 벌이 어긋난다.

**신규 `frontend/src/lib/appVersion.ts`**

| 내보내는 것 | 책임 |
|---|---|
| `formatVersionTimestamp(date: Date): string` | 로컬 시각을 `YYYYMMDD_HHmmss`로. 순수 함수 — 테스트가 직접 부른다. |
| `appVersion: string` | `__APP_BUILD_ISO__`를 파싱해 포맷한 상수 |

`frontend/src/vite-env.d.ts`에 전역 선언을 추가한다:

```ts
declare const __APP_BUILD_ISO__: string;
```

PowerShell과 JS 양쪽에서 포맷하지만 입력이 같은 순간이므로 VERSION.txt와 화면 값이 일치한다. 서로 다른 언어의 출력 파일이라 포맷 코드 자체를 공유할 방법은 없다.

## 2. 화면 표시

`frontend/src/App.tsx` 헤더에서 `<h1>` 바로 뒤, 사이클 요약 앞에 넣는다.

```
Fastening parameter optimizer  20260802_143012  CYCLE-NORMAL-001 / MODEL-A / P10 / S01
                               ^^^^^^^^^^^^^^^
                               text-[11px] font-mono text-slate-400
```

제목 줄은 이미 `flex min-w-0 items-baseline gap-3`이므로 형제 하나를 더 넣으면 된다. 버전은 `shrink-0`으로 두어 사이클 요약이 길어져도 잘리지 않게 한다 — 잘린 타임스탬프는 쓸모가 없다.

dev 서버에서는 서버 기동 시각이 그대로 보인다. `dev` 같은 접미사는 붙이지 않는다. 값 자체가 "이 번들이 만들어진 시각"이라는 뜻이고, 접미사는 정보를 더하지 않는다.

## 3. 빌드 산출물

`scripts/build_exe.ps1`을 고친다.

- 저장소 밖 `..\..\outputs` 경로를 버리고 `releases/`를 쓴다. `Resolve-Path`가 없는 경로에서 실패하던 문제도 같이 사라진다.
- PyInstaller가 결과물을 만들어낸 **뒤**, 그것을 복사해 넣기 직전에 `releases/` 내용을 통째로 비운다. 기존 `FOSIM_20260726_124309`도 여기서 없어진다. 프론트엔드 빌드나 테스트보다 앞에서 비우면 그 단계가 실패했을 때 어제의 배포 가능한 zip마저 사라진 빈 폴더만 남는다. 성공한 빌드 뒤에 `releases/`가 이번 빌드의 결과물만 담는다는 보장은 그대로다.
- 다시 채우는 것은 고정 이름 셋뿐이다.

| 경로 | 내용 |
|---|---|
| `releases/FOSIM/` | PyInstaller 산출 폴더 |
| `releases/FOSIM-exe.zip` | 위 폴더의 압축본 |
| `releases/VERSION.txt` | 버전과 빌드 메타데이터 |

zip 파일명에는 버전을 넣지 않는다. 버전은 VERSION.txt와 앱 헤더에만 남는다. 파일명에 버전이 박히면 배포 링크가 빌드마다 바뀌고, 옛 zip이 쌓여 어느 것이 최신인지 파일 목록만 봐서는 알 수 없다.

`releases/`는 이미 `.gitignore` 대상이라 산출물이 저장소로 들어가지 않는다.

VERSION.txt 형식은 기존 파일을 그대로 따른다:

```
FOSIM
Version: <YYYYMMDD_HHmmss>
Format: YYYYMMDD_HHmmss
Build source: <backend\dist\FOSIM 절대경로>
Package: <releases\FOSIM-exe.zip 절대경로>
Created: <yyyy-MM-dd HH:mm:ss>
```

## 4. 테스트

`frontend/scripts/test_frontend_format.mjs`에 추가한다. 이 러너의 Node 타입 스트리핑은 JSX를 처리하지 못하므로 `.ts` 순수 함수는 import하고 `.tsx`는 `readFileSync` + `assert.match`로 본다 — 기존 관례 그대로다.

- `formatVersionTimestamp(new Date(2026, 7, 2, 14, 30, 12))` → `"20260802_143012"`
- 한 자리 수 zero-padding: `new Date(2026, 0, 5, 9, 8, 7)` → `"20260105_090807"`
- `App.tsx`가 `appVersion`을 쓰는지 정규식 단언

`build_exe.ps1`은 자동 테스트하지 않는다. PyInstaller 실행에 수 분이 걸려 테스트 러너에 넣을 수 없다. 스크립트 변경은 실제 빌드 1회로 확인한다.

`define` 배선 자체도 검증한다. `frontend/vite.config.js`에서 `define` 블록이 사라져도 빌드와 테스트는 초록으로 통과하지만, 번들은 `new Date()` 폴백을 타서 헤더가 "페이지를 연 시각"을 보여주게 된다 — 새로고침할 때마다 값이 바뀌고 VERSION.txt와도 어긋난다. 테스트가 `vite.config.js`를 읽어 `__APP_BUILD_ISO__` 키가 살아 있는지 단언한다.

## 빌드 실패 처리

PowerShell의 `$ErrorActionPreference = "Stop"`은 네이티브 실행 파일의 0이 아닌 종료 코드를 잡지 못한다. `npm run build`가 TypeScript 오류로 죽어도 스크립트는 계속 진행하고, `frontend/dist`에는 직전 빌드 결과물이 남아 있으므로 PyInstaller가 그것을 포장한다. 결과적으로 VERSION.txt는 새 타임스탬프를 갖는데 exe 헤더는 옛 버전을 보여준다 — 이 기능이 막으려던 바로 그 불일치다. 테스트가 빨간 채로 릴리스가 나가는 것도 같은 구멍이다.

모든 네이티브 명령(`npm install`, `npm test`, `npm run build`, `pytest`, `PyInstaller`)은 `$LASTEXITCODE`를 확인해 실패한 단계 이름과 함께 예외를 던지는 헬퍼로 감싼다.

## 범위 밖

- semver(`package.json`의 `0.1.0`, 백엔드 `main.py`의 `version="0.1.0"`) 체계는 건드리지 않는다. 빌드 타임스탬프와 목적이 다르다.
- git 커밋 해시 표시. 요청 범위 밖이고, 타임스탬프만으로 빌드를 특정할 수 있다.
