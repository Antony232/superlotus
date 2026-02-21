# 使用 Python 3.11.14 作为基础镜像
FROM python:3.11.14

# 设置工作目录（容器内的路径）
WORKDIR /app

# 将当前目录下的所有文件复制到容器的工作目录
COPY . /app

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 声明容器运行时监听的端口（根据你的项目实际端口修改，例如 5000）
EXPOSE 8080

# 容器启动时执行的命令
CMD ["python", "bot_main.py"]