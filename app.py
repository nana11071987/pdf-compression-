"""PDF 壓縮 API（Flask + Ghostscript）

GET /  → 拖曳上傳網頁
POST /compress?level=ebook
  - Header: Authorization: Bearer <API_TOKEN>
  - Body: PDF 檔案（直接當作 request body，或用 multipart 欄位 file）
  - 回傳：壓縮後的 PDF（若壓縮後反而更大，就回傳原檔）

level 可選：screen（最小）/ ebook（建議）/ printer（較高品質）
"""
import os
import subprocess
import tempfile

from flask import Flask, Response, abort, request

app = Flask(__name__)

API_TOKEN = os.environ.get("API_TOKEN", "")
MAX_MB = int(os.environ.get("MAX_MB", "100"))
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024

LEVELS = {"screen", "ebook", "printer"}

PAGE = """<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PDF 壓縮</title>
<style>
body{font-family:system-ui,"Noto Sans TC",sans-serif;max-width:560px;margin:0 auto;padding:24px 16px;background:#fafaf8;color:#222}
h1{font-size:1.4rem}
label{display:block;margin:14px 0 4px;font-size:.9rem;color:#555}
input,select{width:100%;padding:10px;border:1px solid #ccc;border-radius:8px;font-size:1rem;box-sizing:border-box}
#drop{margin-top:16px;border:2px dashed #999;border-radius:12px;padding:36px 12px;text-align:center;cursor:pointer;background:#fff}
#drop.over{border-color:#2a7;background:#eefaf3}
#status{margin-top:16px;line-height:1.6}
a.dl{display:inline-block;margin-top:8px;padding:10px 16px;background:#2a7;color:#fff;border-radius:8px;text-decoration:none}
small{color:#777}
</style></head><body>
<h1>PDF 壓縮</h1>
<label>密碼（API_TOKEN，只需輸入一次，會記在這個瀏覽器）</label>
<input id="token" type="password" autocomplete="off">
<label>壓縮等級</label>
<select id="level">
<option value="ebook">ebook（建議）</option>
<option value="screen">screen（最小）</option>
<option value="printer">printer（畫質較高）</option>
</select>
<div id="drop">把 PDF 拖到這裡，或點一下選擇檔案
<input id="file" type="file" accept="application/pdf" hidden></div>
<div id="status"></div>
<small>第一次使用若伺服器在休眠，需等約 1 分鐘。</small>
<script>
const $=id=>document.getElementById(id);
try{$("token").value=localStorage.getItem("tok")||""}catch(e){}
const mb=n=>(n/1048576).toFixed(2)+" MB";
async function run(f){
  if(!f)return;
  const tok=$("token").value.trim();
  try{localStorage.setItem("tok",tok)}catch(e){}
  $("status").textContent="壓縮中…（"+f.name+"，"+mb(f.size)+"）";
  try{
    const r=await fetch("/compress?level="+$("level").value,{method:"POST",
      headers:tok?{Authorization:"Bearer "+tok}:{},body:f});
    if(!r.ok){$("status").textContent="失敗（"+r.status+"）："+(r.status==401?"密碼不正確":await r.text().then(t=>t.replace(/<[^>]*>/g,"").trim().slice(0,120)));return}
    const b=await r.blob();
    const name=f.name.replace(/\\.pdf$/i,"")+"_compressed.pdf";
    const u=URL.createObjectURL(b);
    const pct=Math.round((1-b.size/f.size)*100);
    $("status").innerHTML="完成：<b>"+mb(f.size)+" → "+mb(b.size)+"</b>"+(pct>0?"（減少 "+pct+"%）":"（無法再壓縮，已回傳原檔）")+"<br><a class='dl' href='"+u+"' download='"+name+"'>下載 "+name+"</a>";
  }catch(e){$("status").textContent="連線失敗："+e}
}
const d=$("drop");
d.onclick=()=>$("file").click();
$("file").onchange=e=>run(e.target.files[0]);
d.ondragover=e=>{e.preventDefault();d.classList.add("over")};
d.ondragleave=()=>d.classList.remove("over");
d.ondrop=e=>{e.preventDefault();d.classList.remove("over");run(e.dataTransfer.files[0])};
</script></body></html>"""



def check_auth():
    if not API_TOKEN:
        return  # 沒設定 token 就不驗證（只建議本機測試用）
    if request.headers.get("Authorization", "") != f"Bearer {API_TOKEN}":
        abort(401)


@app.get("/")
def home():
    return Response(PAGE, mimetype="text/html")


@app.get("/health")
def health():
    return "PDF compressor is running"


@app.post("/compress")
def compress():
    check_auth()

    level = request.args.get("level", "ebook")
    if level not in LEVELS:
        abort(400, "level 必須是 screen / ebook / printer")

    # 支援 multipart（欄位 file）或直接傳檔案內容
    if "file" in request.files:
        data = request.files["file"].read()
    else:
        data = request.get_data()
    if not data.startswith(b"%PDF"):
        abort(400, "這不是 PDF 檔案")

    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.pdf")
        dst = os.path.join(tmp, "out.pdf")
        with open(src, "wb") as f:
            f.write(data)

        cmd = [
            "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{level}", "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={dst}", src,
        ]
        try:
            subprocess.run(cmd, check=True, timeout=240)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            abort(500, "壓縮失敗")

        with open(dst, "rb") as f:
            out = f.read()

    # 壓縮後反而更大就回傳原檔
    result = out if len(out) < len(data) else data
    return Response(
        result,
        mimetype="application/pdf",
        headers={
            "X-Original-Size": str(len(data)),
            "X-Compressed-Size": str(len(result)),
            "Content-Disposition": 'attachment; filename="compressed.pdf"',
        },
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
