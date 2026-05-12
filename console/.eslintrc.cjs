// Rules §2 — TS layer boundaries enforced by eslint-plugin-boundaries.
module.exports = {
  root: true,
  parser: "@typescript-eslint/parser",
  plugins: ["boundaries"],
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
};
