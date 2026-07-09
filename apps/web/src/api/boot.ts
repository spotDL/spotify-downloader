import { client } from "./generated/client.gen";
import { installAuthInterceptors } from "./client";

// Composition seam for the CONTRACT C auth interceptors. Lives in the API layer
// (main.tsx / test setup call this) so the app entry point never imports the
// generated client directly — keeping it on the right side of the import
// boundary. Safe from the client.gen ↔ client.ts eval cycle: nothing imports
// this module until boot, by which point the generated client is initialized.
export function installApiInterceptors(): void {
  installAuthInterceptors(client);
}
