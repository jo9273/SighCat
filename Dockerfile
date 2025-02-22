# 使用 Python 3.12 作為基礎環境
FROM python:3.12

# 設定工作目錄
WORKDIR /app

# 複製檔案到容器內
COPY . /app

# 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 啟動 FastAPI 伺服器
# 使用 "exec" + shell 變數，確保 $PORT 被正確解析
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT