// Load backend/.env by path rather than relying on the working directory —
// dotenv's default only finds .env when node is started from backend/.
const path = require("path");
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

const { createClient } = require("@supabase/supabase-js");

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;

// createClient's own "supabaseUrl is required" says nothing about where to look.
const missing = ["SUPABASE_URL", "SUPABASE_KEY"].filter((k) => !process.env[k]);
if (missing.length > 0) {
  console.error(
    `Missing environment variable(s): ${missing.join(", ")}\n` +
      "Add them to backend/.env as plain KEY=value lines " +
      "(no const, no quotes, no semicolons).",
  );
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

module.exports = supabase;
