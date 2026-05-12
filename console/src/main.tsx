import React from "react";
import ReactDOM from "react-dom/client";
import { LoadShift } from "./application/shift-load";
import { HttpShiftClient } from "./infrastructure/http-shift-client";
import { ShiftViewPanel } from "./presentation/ShiftView";

const loadShift = new LoadShift(
  new HttpShiftClient(import.meta.env.VITE_API_BASE ?? "http://localhost:8000"),
);
const propertyId = import.meta.env.VITE_PROPERTY_ID ?? "";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ShiftViewPanel propertyId={propertyId} loadShift={loadShift} />
  </React.StrictMode>,
);
