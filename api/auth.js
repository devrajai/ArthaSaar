const crypto=require("crypto");
/* hardcoded password hash removed — set ARTHASAAR_PASSWORD_SHA256 in the environment if this endpoint is used again */
const fallbackSecret = crypto.randomBytes(32).toString("hex");
function ph(){return process.env.ARTHASAAR_PASSWORD_SHA256||""}
function sec(){return process.env.ARTHASAAR_AUTH_SECRET||ph()||fallbackSecret}
function hash(s){return crypto.createHash("sha256").update(String(s)).digest("hex")}
function sig(v){return crypto.createHmac("sha256",sec()).update(v).digest("base64url")}
function ok(req){const m=(req.headers.cookie||"").match(/(?:^|;\s*)as_auth=([^;]+)/);if(!m)return false;const p=m[1].split(".");if(p.length!==2)return false;const exp=Number(Buffer.from(p[0],"base64url").toString());if(!Number.isFinite(exp)||exp<Date.now())return false;const a=Buffer.from(p[1]),b=Buffer.from(sig(p[0]));return a.length===b.length&&crypto.timingSafeEqual(a,b)}
function ck(v,max){return"as_auth="+v+"; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age="+max}
module.exports=async function(req,res){
 if(req.method==="GET")return ok(req)?res.status(200).json({ok:true}):res.status(401).json({ok:false});
 if(req.method==="POST"){let b=req.body||{};if(typeof b==="string")try{b=JSON.parse(b)}catch(e){b={}}if(hash(String(b.password||""))!==ph())return res.status(401).json({ok:false});const p=Buffer.from(String(Date.now()+14400000)).toString("base64url");res.setHeader("Set-Cookie",ck(p+"."+sig(p),14400));return res.status(200).json({ok:true})}
 if(req.method==="DELETE"){res.setHeader("Set-Cookie",ck("x",0));return res.status(200).json({ok:true})}
 return res.status(405).end()
};