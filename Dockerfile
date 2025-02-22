# 使用 Python 3.12 作為基礎映像
FROM python:3.12

# 設定工作目錄
WORKDIR /app

# 複製專案檔案
COPY . /app

# 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# **不要** 強制設定 ENV PORT=8080，讓 Cloud Run 自己注入！
# ENV PORT=8080  <-- 必須刪除

# 用 exec 確保能正確啟動
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT