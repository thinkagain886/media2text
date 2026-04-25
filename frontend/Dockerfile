# =============================================================================
# 前端镜像构建说明（多阶段构建 Dockerfile）
# -----------------------------------------------------------------------------
# • 「多阶段」= 第一阶段用 Node 编译 Vue，第二阶段只要 Nginx + 静态文件，镜像更小。
# • 最终运行的容器里**没有** Node，只有 Nginx 提供网页。
# =============================================================================

# ----- 第一阶段：builder（别名），用于 npm install + npm run build -----
FROM node:18-alpine AS builder

WORKDIR /app

# 先复制 package.json / lock，依赖不变时可利用 Docker 缓存
COPY package*.json ./
RUN npm install

# 再复制全部前端源码并执行生产构建，生成 dist 目录
COPY . .
RUN npm run build

# ----- 第二阶段：正式运行镜像，基于 Nginx 官方精简镜像 -----
FROM nginx:alpine

# 从第一阶段 builder 里拷贝编译结果到 Nginx 默认静态根目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制本站点的 Nginx 配置（含 /api 反向代理到后端容器）
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Nginx 前台运行，这样容器进程不退出（Docker 容器要有前台主进程）
CMD ["nginx", "-g", "daemon off;"]
