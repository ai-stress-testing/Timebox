import { useState } from "react";
import { use_unlock } from "../../Hooks/use-vault";
import {
  is_unauthorized,
  to_error_message,
} from "../../Services/api-client";
import { KeyDropZone } from "./key-drop-zone";
import { read_keyfile } from "./read-keyfile";

/** Returning user: point at the key file to unlock. */
export function UnlockPanel() {
  const unlock = use_unlock();
  const [error, set_error] = useState<string | null>(null);

  const handle_file = async (file: File) => {
    set_error(null);
    const result = await read_keyfile(file);
    if (!result.ok) {
      set_error(result.message);
      return;
    }
    try {
      await unlock.mutateAsync(result.keyfile);
    } catch (cause) {
      const message = is_unauthorized(cause)
        ? "That key doesn't open this vault."
        : to_error_message(cause);
      set_error(message);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <KeyDropZone
        disabled={unlock.isPending}
        on_file={(file) => void handle_file(file)}
      />
      {unlock.isPending ? <p className="text-sm text-mid">Unlocking…</p> : null}
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
    </div>
  );
}
