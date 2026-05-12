// Layer: infrastructure. Implements ShiftClient port.
import type { ShiftView } from "../domain/types";
import type { ShiftClient } from "../application/shift-load";

export class HttpShiftClient implements ShiftClient {
  constructor(private readonly baseUrl: string) {}
  async load(propertyId: string): Promise<ShiftView> {
    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 5000); // Rules §4 — timeout everywhere
    try {
      const r = await fetch(
        `${this.baseUrl}/v1/properties/${propertyId}/shift`,
        { signal: ctrl.signal },
      );
      if (!r.ok) throw new Error(`shift load failed: ${r.status}`);
      return (await r.json()) as ShiftView;
    } finally {
      clearTimeout(timeout);
    }
  }
}
