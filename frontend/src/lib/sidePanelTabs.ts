import type { ReactNode } from "react";

export type SidePanelTabId = "input" | "group" | "analysis";

export type SidePanelTab = {
  id: SidePanelTabId;
  label: string;
  /** 렌더링할 패널들. 비어 있으면 disabled가 true다. */
  content: ReactNode[];
  /** 그룹 탭의 제외 건수. 0이거나 없으면 생략한다. */
  badge?: number;
  disabled: boolean;
};

export type SidePanelTabsProps = {
  importPanel?: ReactNode;
  cycleSelector?: ReactNode;
  groupOverview?: ReactNode;
  diagnosis?: ReactNode;
  notes?: ReactNode;
  excludedCount?: number;
};

function present(...items: Array<ReactNode | undefined>): ReactNode[] {
  return items.filter((item) => item !== undefined && item !== null && item !== false);
}

export function sidePanelTabs(props: SidePanelTabsProps): SidePanelTab[] {
  const input = present(props.importPanel, props.cycleSelector);
  const group = present(props.groupOverview);
  const analysis = present(props.diagnosis, props.notes);

  const groupTab: SidePanelTab = {
    id: "group",
    label: "그룹",
    content: group,
    disabled: group.length === 0,
  };
  if (props.excludedCount) {
    groupTab.badge = props.excludedCount;
  }

  return [
    { id: "input", label: "입력", content: input, disabled: input.length === 0 },
    groupTab,
    { id: "analysis", label: "분석", content: analysis, disabled: analysis.length === 0 },
  ];
}
