import { use_vault_status } from "../Hooks/use-vault";
import { to_error_message } from "../Services/api-client";
import { GeneratePanel } from "../Components/vault/generate-panel";
import { UnlockPanel } from "../Components/vault/unlock-panel";

function VaultHeading() {
  return (
    <header className="text-center">
      <h1
        className="font-display text-display tracking-hug font-black
          bg-clip-text text-transparent
          [background-image:var(--tb-gradient-accent)]"
      >
        Timebox
      </h1>
      <p className="mt-2 text-sm text-mid">
        One user. One key. Zero surveillance.
      </p>
    </header>
  );
}

function KeyWarning() {
  return (
    <p
      className="rounded-md border border-warn/40 bg-warn/10 px-4 py-3
        text-sm text-warn"
    >
      Your key file is your only way in. Lose it and your data is gone —
      that&rsquo;s the point.
    </p>
  );
}

/** Shown whenever there is no session token. */
export function VaultPage() {
  const status_query = use_vault_status();
  return (
    <main className="flex min-h-dvh items-center justify-center p-6">
      <section
        aria-label="Vault"
        className="animate-pop-in flex w-full max-w-md flex-col gap-6
          rounded-xl border border-edge bg-surface-1 p-8 shadow-raised"
      >
        <VaultHeading />
        {status_query.isPending ? (
          <p className="text-center text-sm text-mid">Checking the vault…</p>
        ) : null}
        {status_query.isError ? (
          <p role="alert" className="text-center text-sm text-danger">
            {to_error_message(status_query.error)}
          </p>
        ) : null}
        {status_query.data?.registered === false ? <GeneratePanel /> : null}
        {status_query.data?.registered === true ? <UnlockPanel /> : null}
        <KeyWarning />
      </section>
    </main>
  );
}
