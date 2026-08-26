import "jsr:@supabase/functions-js/edge-runtime.d.ts";

Deno.serve(()=>new Response(
 JSON.stringify({error:"Boleto/Bolix foi desativado. Use Pix QR Code ou cartão."}),
 {status:410,headers:{"Content-Type":"application/json"}}
));
