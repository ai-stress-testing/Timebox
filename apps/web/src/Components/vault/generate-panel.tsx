import { useState } from "react";
import { use_generate_key, use_unlock } from "../../Hooks/use-vault";
import { download_json } from "../../lib/download";
import { to_error_message } from "../../Services/api-client";
import { Button } from "../ui/button";

/** First run: mint a key file, download it, then unlock with it. */
export function GeneratePanel() {
  const generate = use_generate_key();
  const unlock = use_unlock();
  const [error, set_error] = useState<string | null>(null);
  const busy = generate.isPending || unlock.isPending;

  const handle_generate = async () => {
    set_error(null);
    try {
      const { keyfile } = await generate.mutateAsync();
      download_json("timebox.key", keyfile);
      await unlock.mutateAsync(keyfile);
    } catch (cause) {
      set_error(to_error_message(cause));
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-mid">
        No identity exists yet. Generate your key file — it downloads as{" "}
        <code className="font-mono text-accent-2">timebox.key</code> and
        unlocks Timebox immediately.
      </p>
      <Button
        variant="primary"
        onClick={() => void handle_generate()}
        disabled={busy}
        className="w-full py-3 text-base"
      >
        {busy ? "Generating…" : "Generate key"}
      </Button>
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
    </div>
  );
}
