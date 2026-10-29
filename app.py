"""PDF 壓縮 API（Flask + Ghostscript）

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


def check_auth():
    if not API_TOKEN:
        return  # 沒設定 token 就不驗證（只建議本機測試用）
    if request.headers.get("Authorization", "") != f"Bearer {API_TOKEN}":
        abort(401)


@app.get("/")
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
