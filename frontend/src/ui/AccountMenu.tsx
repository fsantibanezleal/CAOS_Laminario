// The account in the masthead (R-1201): "Sign in" for a visitor; for someone signed in, their name, which opens a
// short list: their contributions (for those who may contribute) and sign out. A disclosure (a button and the list it
// shows), not an application menu: Tab moves through the links, Escape and a click outside close it.
import { useEffect, useId, useRef, useState } from "react";
import { Link, useLocation } from "wouter";
import { signInHref } from "../account/api";
import { useSession } from "../account/session";
import { useI18n } from "../i18n";
import styles from "./AccountMenu.module.css";
import { Glyph } from "./Icon";

export function AccountMenu() {
  const { t } = useI18n();
  const session = useSession();
  const [location, navigate] = useLocation();
  const [open, setOpen] = useState(false);
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return undefined;
    const outside = (e: PointerEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    const escape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  useEffect(() => setOpen(false), [location]);

  if (session.state === "loading") return <span className={styles.placeholder} aria-hidden="true" />;
  const account = session.account;
  if (!account) {
    const here = location.startsWith("/signin") || location.startsWith("/join") ? "/contribute" : location;
    return (
      <Link href={signInHref(here)} className={styles.signIn}>
        <Glyph name="account" size={20} />
        <span>{t("account.signin.title")}</span>
      </Link>
    );
  }
  return (
    <div ref={root} className={styles.account}>
      <button ref={button} type="button" className={styles.trigger} aria-expanded={open} aria-controls={id}
        onClick={() => setOpen((v) => !v)}>
        <Glyph name="account" size={20} />
        <span className={styles.name}>{account.display_name}</span>
        <Glyph name="chevron-down" size={16} />
      </button>
      <div id={id} className={styles.panel} hidden={!open}>
        <p className={styles.who}>
          <span>{account.email}</span>
          <span className={styles.role}>{t(`account.role.${account.role}`)}</span>
        </p>
        <ul>
          {session.can("submit") ? (
            <li><Link href="/contribute" className={styles.item}><Glyph name="draft" size={20} />
              <span>{t("contribute.mine")}</span></Link></li>
          ) : null}
          <li>
            <button type="button" className={styles.item} onClick={async () => {
              setOpen(false);
              await session.signOut();
              if (location.startsWith("/contribute")) navigate("/");
            }}>
              <Glyph name="sign-out" size={20} />
              <span>{t("account.signout")}</span>
            </button>
          </li>
        </ul>
      </div>
    </div>
  );
}
