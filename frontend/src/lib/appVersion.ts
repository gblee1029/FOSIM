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
