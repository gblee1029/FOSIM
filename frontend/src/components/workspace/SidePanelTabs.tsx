import { useEffect, useState } from "react";

import { sidePanelTabs, type SidePanelTabId, type SidePanelTabsProps } from "../../lib/sidePanelTabs";

export function SidePanelTabs(props: SidePanelTabsProps) {
  // useMemo를 쓰지 않는다. props는 매 렌더마다 새 JSX 객체를 담고 오므로 의존 배열이
  // 항상 바뀌어 메모이제이션이 되지 않는다. 계산도 배열 3개 만드는 수준이라 값싸다.
  const tabs = sidePanelTabs(props);
  const [activeId, setActiveId] = useState<SidePanelTabId>("input");

  // 보던 탭이 비활성으로 바뀌면(예: 새 임포트로 group_summary가 사라짐) 입력 탭으로 되돌린다.
  const activeTab = tabs.find((tab) => tab.id === activeId);
  useEffect(() => {
    if (activeTab?.disabled) setActiveId("input");
  }, [activeTab?.disabled]);

  const shown = activeTab && !activeTab.disabled ? activeTab : tabs[0];

  return (
    <div className="flex min-h-0 flex-1 flex-col rounded-md border border-slate-200 bg-white shadow-sm">
      <div className="flex shrink-0 gap-1 border-b border-slate-100 p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            disabled={tab.disabled}
            onClick={() => setActiveId(tab.id)}
            className={
              "flex flex-1 items-center justify-center gap-1 rounded px-2 py-1.5 text-xs font-medium transition " +
              (tab.id === shown?.id
                ? "bg-graphite text-white"
                : tab.disabled
                  ? "cursor-not-allowed text-slate-300"
                  : "text-steel hover:bg-slate-100")
            }
          >
            {tab.label}
            {tab.badge !== undefined && (
              <span className="rounded-full bg-amber-100 px-1.5 text-[10px] font-semibold text-amber-800">
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-2">
        {shown?.content.map((node, index) => <div key={index}>{node}</div>)}
      </div>
    </div>
  );
}
