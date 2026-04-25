# =============================================================================
# 后端镜像构建说明（Dockerfile）
# -----------------------------------------------------------------------------
# • Dockerfile =「做菜的菜谱」：从上到下每一步生成一层镜像。
# • build context 一般是 backend 文件夹（见 docker-compose 里 backend.build.context）。
# • FROM = 从哪个官方基础镜像开始（这里用精简版 Python 3.11）。
# =============================================================================

# 基础镜像：Debian + Python 3.11，slim = 体积较小（不含多余工具）
FROM python:3.11-slim

# RUN = 在这一层镜像里执行 shell 命令（合并一条可减少镜像层数）
# 安装 FFmpeg：音视频转码；装完删掉 apt 缓存减小体积
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# WORKDIR：后面 CMD/COPY 的默认目录，容器启动后也在此目录
WORKDIR /app

# 先只复制依赖清单：这样依赖不变时 Docker 可命中缓存，重建更快
COPY requirements.txt .

# 安装 PyTorch CPU 版（体积大），再从 requirements 装其余包
# --no-cache-dir 减小镜像内 pip 缓存
RUN pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --no-cache-dir \
    && pip install -r requirements.txt --no-cache-dir

# 再复制后端全部源码（代码常改，放后面利于缓存前几步）
COPY . .

# 创建输出、临时目录（若没有）
RUN mkdir -p output temp

# EXPOSE：声明容器内监听端口（文档性质；真正映射端口在 compose 里 ports）
EXPOSE 8000

# CMD：容器启动时执行的默认命令（可被 docker run 覆盖）
# 0.0.0.0 表示监听所有网卡，便于宿主机和其它容器访问
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
