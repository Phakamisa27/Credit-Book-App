const path = require("path");
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

console.log("URL exists:", !!process.env.SUPABASE_URL);
console.log("KEY exists:", !!process.env.SUPABASE_KEY);

const supabase = require("./supabaseClient");

async function testSupabase() {
  const { data, error } = await supabase.from("users").select("*").limit(5);

  if (error) {
    console.error("❌ Supabase connection failed:");
    console.error(error);
    return;
  }

  console.log("✅ Supabase connection successful!");
  console.log("Users:", data);

  const { error: insertError } = await supabase
    .from("users")
    .select("*")
    .limit(5);

  if (insertError) {
    console.error("insert failed");
    console.error(insertError);
    return;
  }
  console.log("user created successfully");
}

testSupabase();
