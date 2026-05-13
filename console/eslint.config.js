// Rules §2 — TS layer boundaries enforced by eslint-plugin-boundaries (flat config v9+).
import boundaries from "eslint-plugin-boundaries";
import tsParser from "@typescript-eslint/parser";

export default [
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: { boundaries },
    settings: {
      "boundaries/elements": [
        { type: "domain", pattern: "src/domain/*" },
        { type: "application", pattern: "src/application/*" },
        { type: "infrastructure", pattern: "src/infrastructure/*" },
        { type: "presentation", pattern: "src/presentation/*" },
      ],
    },
    rules: {
      "boundaries/element-types": [
        2,
        {
          default: "disallow",
          rules: [
            { from: "domain", allow: ["domain"] },
            { from: "application", allow: ["domain", "application"] },
            { from: "infrastructure", allow: ["domain", "application", "infrastructure"] },
            { from: "presentation", allow: ["application", "domain", "presentation"] },
          ],
        },
      ],
    },
  },
];
