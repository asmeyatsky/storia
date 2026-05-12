// Layer: application. Depends on domain only.
import type { ShiftView } from "../domain/types";

export interface ShiftClient {
  load(propertyId: string): Promise<ShiftView>;
}

export class LoadShift {
  constructor(private readonly client: ShiftClient) {}
  async exec(propertyId: string): Promise<ShiftView> {
    return this.client.load(propertyId);
  }
}
