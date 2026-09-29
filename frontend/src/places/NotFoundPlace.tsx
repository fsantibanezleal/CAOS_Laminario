// An address that names no place (or no cabinet or drawer of the tree): said plainly, with the way back.
import { Link } from "wouter";
import { useI18n } from "../i18n";
import { Place } from "../router/Place";
import { EmptyState } from "../ui/Feedback";

export function NotFoundPlace() {
  const { t } = useI18n();
  return (
    <Place title={t("notfound.title")}>
      <EmptyState icon="life" title={t("notfound.title")}
        action={<Link href="/">{t("notfound.home")}</Link>}>
        {t("notfound.body")}
      </EmptyState>
    </Place>
  );
}
