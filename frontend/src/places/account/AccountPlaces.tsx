// The account places (R-1201): sign in, join from an invitation link, ask for a password reset, and set a new
// password from the reset link. Each is one short form on a card of paper; a refusal is said above the form in the
// page's language (the server's own words only for a refusal the interface has no words for), and the focus moves to
// it so a screen reader reads it. Accounts are invitation-only: the sign-in place says so, and how to get one.
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, useLocation, useSearch } from "wouter";
import { accountApi, MIN_PASSWORD_LENGTH, passwordProblem, refusalKey, safeNext } from "../../account/api";
import { useSession } from "../../account/session";
import { ApiError } from "../../api/client";
import { useI18n } from "../../i18n";
import type { MessageKey } from "../../i18n/en";
import { Place } from "../../router/Place";
import { Button } from "../../ui/Button";
import { TextField } from "../../ui/Field";
import { Glyph } from "../../ui/Icon";
import styles from "./Account.module.css";

function useRefusal() {
  const { t } = useI18n();
  const [message, setMessage] = useState<string | null>(null);
  const say = (error: unknown) => {
    if (error instanceof ApiError) {
      const key = refusalKey(error.code);
      setMessage(key ? t(key as MessageKey) : error.status >= 500 || error.status === 0
        ? t("account.error.server") : error.reason ?? t("account.error.server"));
    } else {
      setMessage(t("account.error.network"));
    }
  };
  return { message, say, clear: () => setMessage(null), set: setMessage };
}

function Card({ title, lead, refusal, done, children, foot }: { title: string; lead?: ReactNode; refusal: string | null;
  done?: ReactNode; children?: ReactNode; foot?: ReactNode }) {
  const alertRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (refusal) alertRef.current?.focus();
  }, [refusal]);
  return (
    <Place title={title}>
      <section className={styles.card}>
        {lead ? <p className={styles.lead}>{lead}</p> : null}
        {refusal ? (
          <div ref={alertRef} tabIndex={-1} role="alert" className={styles.refusal}>
            <Glyph name="warning" size={20} />
            <span>{refusal}</span>
          </div>
        ) : null}
        {done ?? children}
        {foot ? <div className={styles.foot}>{foot}</div> : null}
      </section>
    </Place>
  );
}

export function SignInPlace() {
  const { t } = useI18n();
  const search = new URLSearchParams(useSearch());
  const next = safeNext(search.get("next"));
  const [, navigate] = useLocation();
  const session = useSession();
  const refusal = useRefusal();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (session.account) navigate(next, { replace: true });
  }, [session.account, next, navigate]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    refusal.clear();
    setBusy(true);
    try {
      await accountApi.signIn(email.trim(), password);
      await session.refresh();
    } catch (error) {
      refusal.say(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title={t("account.signin.title")} lead={t("account.signin.lead")} refusal={refusal.message}
      foot={<>
        <Link href="/forgot-password">{t("account.signin.forgot")}</Link>
        <p className={styles.note}>{t("account.signin.invitationOnly")}</p>
      </>}>
      <form className={styles.form} onSubmit={submit} noValidate>
        <TextField label={t("account.email")} type="email" autoComplete="username" required value={email}
          onChange={(e) => setEmail(e.target.value)} />
        <TextField label={t("account.password")} type="password" autoComplete="current-password" required
          value={password} onChange={(e) => setPassword(e.target.value)} />
        <Button type="submit" variant="primary" busy={busy} disabled={!email || !password} icon="account">
          {t("account.signin.action")}
        </Button>
      </form>
    </Card>
  );
}

export function JoinPlace() {
  const { t } = useI18n();
  const token = new URLSearchParams(useSearch()).get("token") ?? "";
  const [, navigate] = useLocation();
  const session = useSession();
  const refusal = useRefusal();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [repeated, setRepeated] = useState("");
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const problem = passwordProblem(password, email, repeated);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    refusal.clear();
    if (problem || !name.trim() || !email.trim()) return;
    setBusy(true);
    try {
      await accountApi.register(token, email.trim(), password, name.trim());
      await accountApi.signIn(email.trim(), password);
      await session.refresh();
      navigate("/contribute", { replace: true });
    } catch (error) {
      refusal.say(error);
    } finally {
      setBusy(false);
    }
  };

  if (!token) {
    return <Card title={t("account.join.title")} refusal={t("account.join.noToken")}
      foot={<Link href="/signin">{t("account.signin.title")}</Link>} />;
  }
  const passwordError = tried && problem && problem !== "password.mismatch"
    ? t(`account.${problem}` as MessageKey, { count: MIN_PASSWORD_LENGTH }) : undefined;
  return (
    <Card title={t("account.join.title")} lead={t("account.join.lead")} refusal={refusal.message}>
      <form className={styles.form} onSubmit={submit} noValidate>
        <TextField label={t("account.displayName")} autoComplete="name" required maxLength={80} value={name}
          hint={t("account.displayName.hint")} error={tried && !name.trim() ? t("field.required") : undefined}
          onChange={(e) => setName(e.target.value)} />
        <TextField label={t("account.email")} type="email" autoComplete="email" required value={email}
          hint={t("account.join.emailHint")} error={tried && !email.trim() ? t("field.required") : undefined}
          onChange={(e) => setEmail(e.target.value)} />
        <TextField label={t("account.newPassword")} type="password" autoComplete="new-password" required
          hint={t("account.password.rules", { count: MIN_PASSWORD_LENGTH })} error={passwordError} value={password}
          onChange={(e) => setPassword(e.target.value)} />
        <TextField label={t("account.repeatPassword")} type="password" autoComplete="new-password" required
          error={tried && problem === "password.mismatch" ? t("account.password.mismatch") : undefined}
          value={repeated} onChange={(e) => setRepeated(e.target.value)} />
        <Button type="submit" variant="primary" busy={busy} icon="account">{t("account.join.action")}</Button>
      </form>
    </Card>
  );
}

export function ForgotPlace() {
  const { t } = useI18n();
  const refusal = useRefusal();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    refusal.clear();
    setBusy(true);
    try {
      await accountApi.forgot(email.trim());
      setSent(true);
    } catch (error) {
      refusal.say(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title={t("account.forgot.title")} lead={t("account.forgot.lead")} refusal={refusal.message}
      done={sent ? <p role="status" className={styles.done}><Glyph name="check" size={20} />
        <span>{t("account.forgot.sent", { email: email.trim() })}</span></p> : undefined}
      foot={<>
        <Link href="/signin">{t("account.signin.title")}</Link>
        <p className={styles.note}>{t("account.forgot.noMail")}</p>
      </>}>
      <form className={styles.form} onSubmit={submit} noValidate>
        <TextField label={t("account.email")} type="email" autoComplete="email" required value={email}
          onChange={(e) => setEmail(e.target.value)} />
        <Button type="submit" variant="primary" busy={busy} disabled={!email.includes("@")}>
          {t("account.forgot.action")}
        </Button>
      </form>
    </Card>
  );
}

export function ResetPlace() {
  const { t } = useI18n();
  const token = new URLSearchParams(useSearch()).get("token") ?? "";
  const refusal = useRefusal();
  const [password, setPassword] = useState("");
  const [repeated, setRepeated] = useState("");
  const [tried, setTried] = useState(false);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  // The reset link does not name the address, so only the length and the repetition are checked here.
  const problem = passwordProblem(password, "", repeated);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    refusal.clear();
    if (problem) return;
    setBusy(true);
    try {
      await accountApi.reset(token, password);
      setDone(true);
    } catch (error) {
      refusal.say(error);
    } finally {
      setBusy(false);
    }
  };

  if (!token) {
    return <Card title={t("account.reset.title")} refusal={t("account.reset.noToken")}
      foot={<Link href="/forgot-password">{t("account.forgot.title")}</Link>} />;
  }
  return (
    <Card title={t("account.reset.title")} lead={t("account.reset.lead")} refusal={refusal.message}
      done={done ? <p role="status" className={styles.done}><Glyph name="check" size={20} />
        <span>{t("account.reset.done")} <Link href="/signin">{t("account.signin.title")}</Link></span></p>
        : undefined}>
      <form className={styles.form} onSubmit={submit} noValidate>
        <TextField label={t("account.newPassword")} type="password" autoComplete="new-password" required
          hint={t("account.password.rules", { count: MIN_PASSWORD_LENGTH })}
          error={tried && problem === "password.short" ? t("account.password.short", { count: MIN_PASSWORD_LENGTH })
            : undefined}
          value={password} onChange={(e) => setPassword(e.target.value)} />
        <TextField label={t("account.repeatPassword")} type="password" autoComplete="new-password" required
          error={tried && problem === "password.mismatch" ? t("account.password.mismatch") : undefined}
          value={repeated} onChange={(e) => setRepeated(e.target.value)} />
        <Button type="submit" variant="primary" busy={busy}>{t("account.reset.action")}</Button>
      </form>
    </Card>
  );
}
