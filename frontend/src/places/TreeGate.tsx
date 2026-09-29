// A place that needs the tree: a skeleton while it loads, an error with a way to try again, then the place.
import type { ReactNode } from "react";
import { useI18n } from "../i18n";
import type { TreeIndex, TreeState } from "../tree/TreeProvider";
import { Button } from "../ui/Button";
import { Skeleton } from "../ui/Feedback";

export function TreeGate({ tree, children }: { tree: TreeState; children: (tree: TreeIndex) => ReactNode }) {
  const { t } = useI18n();
  if (tree.state === "loading") return <Skeleton lines={6} />;
  if (tree.state === "error") {
    return (
      <div role="alert">
        <p>{t("explore.error")}</p>
        <Button onClick={() => location.reload()}>{t("explore.retry")}</Button>
      </div>
    );
  }
  return <>{children(tree.tree)}</>;
}
