// 賃管特訓の記録の控え（クラウド）。端末ごとのランダムな鍵(key)で保存・読み出し。
// PC(毎朝の指示)は AIニュースの machine 合言葉(x-key)で最新の控えを読む。
import { createClient } from "npm:@supabase/supabase-js@2";
const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
const cors = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "content-type, x-key", "Access-Control-Allow-Methods": "POST, OPTIONS" };
const json = (b: unknown, s = 200) => new Response(JSON.stringify(b), { status: s, headers: { ...cors, "Content-Type": "application/json" } });
const okKey = (k: unknown) => typeof k === "string" && /^[0-9a-f-]{20,64}$/.test(k);
async function sha256(s: string) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });
  const body = await req.json().catch(() => ({}));
  switch (body.action) {
    case "save": {
      if (!okKey(body.key) || typeof body.data !== "object") return json({ error: "bad" }, 400);
      if (JSON.stringify(body.data).length > 3_000_000) return json({ error: "too large" }, 413);
      const { error } = await db.from("chinkan_backup").upsert({ key: body.key, data: body.data, updated_at: new Date().toISOString() });
      return error ? json({ error: error.message }, 400) : json({ ok: true });
    }
    case "load": {
      if (!okKey(body.key)) return json({ error: "bad" }, 400);
      const { data } = await db.from("chinkan_backup").select("data,updated_at").eq("key", body.key).maybeSingle();
      return json({ data: data?.data ?? null, updated_at: data?.updated_at ?? null });
    }
    case "latest": {
      const k = req.headers.get("x-key");
      const { data: role } = k ? await db.from("app_keys").select("role").eq("sha256", await sha256(k)).maybeSingle() : { data: null };
      if (role?.role !== "machine") return json({ error: "unauthorized" }, 401);
      const { data } = await db.from("chinkan_backup").select("key,data,updated_at").order("updated_at", { ascending: false }).limit(1);
      return json(data?.[0] ?? null);
    }
  }
  return json({ error: "unknown action" }, 400);
});
