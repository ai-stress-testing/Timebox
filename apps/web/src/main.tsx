import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "./app";
import "./index.css";

const query_client = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 15_000 },
  },
});

const root_element = document.getElementById("root");
if (root_element) {
  createRoot(root_element).render(
    <StrictMode>
      <QueryClientProvider client={query_client}>
        <App />
      </QueryClientProvider>
    </StrictMode>,
  );
}
