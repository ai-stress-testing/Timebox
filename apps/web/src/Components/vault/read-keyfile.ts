import { keyfile_schema } from "../../lib/api-schemas";
import type { Keyfile } from "../../lib/api-schemas";

export type KeyfileReadResult =
  | { ok: true; keyfile: Keyfile }
  | { ok: false; message: string };

/** Read + zod-validate a user-supplied key file (never trust file input). */
export async function read_keyfile(file: File): Promise<KeyfileReadResult> {
  let text: string;
  try {
    text = await file.text();
  } catch {
    return { ok: false, message: "Could not read that file." };
  }
  let payload: unknown;
  try {
    payload = JSON.parse(text);
  } catch {
    return { ok: false, message: "That file is not valid JSON." };
  }
  const parsed = keyfile_schema.safeParse(payload);
  if (!parsed.success) {
    return { ok: false, message: "That file is not a Timebox key file." };
  }
  return { ok: true, keyfile: parsed.data };
}
