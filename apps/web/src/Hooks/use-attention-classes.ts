import { useQuery } from "@tanstack/react-query";
import { api_request } from "../Services/api-client";
import { attention_class_meta_list_schema } from "../lib/api-schemas";

/** The 3 fixed, boot-seeded attention classes (active/involved/passive) and
 * how the app treats each — static reference data, never mutated from the client. */
export function use_attention_classes() {
  return useQuery({
    queryKey: ["attention-classes"],
    queryFn: () => api_request("/attention-classes", attention_class_meta_list_schema),
  });
}
