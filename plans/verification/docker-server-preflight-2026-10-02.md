# Docker CLI 与目标服务器只读 preflight 证据（2026-10-02）

## 范围

本记录只覆盖本机 Docker CLI 工具安装和候选部署服务器 `yeyuhome` 的只读检查。没有修改 `E:\AI_projects\yeyubakahome_Web`、`new.api.yeyubaka.top`、服务器配置、DNS、Nginx、证书或生产容器。

## 本机 Docker CLI

- Windows 主机：ASUS TUF Gaming F15，i7-13700H，约 32 GiB 内存。
- 磁盘：C 盘可用约 120.45 GiB，E 盘可用约 159.16 GiB。
- 官方 Docker 静态包 `docker-29.8.2.zip` 下载源：`https://download.docker.com/win/static/stable/x86_64/docker-29.8.2.zip`。
- 已安装位置：`E:\AI_projects\tools\docker-cli\bin\docker.exe`。
- `docker --version`：`Docker version 29.8.2, build 7fc2dff`。
- 已将 `E:\AI_projects\tools\docker-cli\bin` 写入当前用户 PATH；仓库 Git 状态保持干净。
- 本地 Docker daemon 不可用：默认 `npipe:////./pipe/docker_engine` 不存在；本机未启动 Docker Desktop/Engine。
- 本地 Compose 插件未安装，因此本机现在只能运行 Docker CLI 客户端，不能执行本地 `docker compose up`。
- 通过 `docker -H ssh://root@yeyuhome info` 只读连接远程 Engine 成功，证明客户端可用于远程运维；未以此执行任何修改操作。

## `yeyuhome` 只读事实

检查时间：本机 `2026-10-02T21:08:11+08:00`；服务器 `2026-10-02T21:08:13+08:00`。

- 系统：Ubuntu 26.04 LTS，x86_64；当前 SSH 检查身份为 root，仅用于只读 preflight。
- 计算资源：2 vCPU。
- 内存：总计约 3.4 GiB，检查时 available 约 1.4 GiB；Swap 约 2 GiB。
- 磁盘：根分区约 49 GiB，已用约 21 GiB，可用约 26 GiB；`/var/lib/docker` 约 1.6 GiB；inode 使用率约 16%。
- Docker：Engine 29.1.3，Compose 2.40.3，overlayfs，Docker 根目录 `/var/lib/docker`。
- 现有运行容器：`meter-vision-web-1`、`meter-vision-backend-1`、`meter-vision-postgres-1`、`yatori-server`、`unified-ai-new-api`、`qinglong`。
- 检查时 Docker stats 观测的容器内存合计约 618 MiB；其中 `meter-vision-backend-1` 约 216 MiB、`qinglong` 约 248 MiB。多个现有容器没有显式内存上限。
- Docker 磁盘统计：8 个镜像、6 个活动镜像，约 10.38 GiB；Build cache 约 7.98 GiB。
- 端口：宿主机 80/443 已由现有 Nginx 监听；现有容器使用 127.0.0.1 的 3000、8000、8001、8080、5700 等端口。
- Nginx 配置测试通过，但没有发现独立的 `api.yeyubaka.top` vhost；`new.api.yeyubaka.top` 是现有站点，不能复用或改写。
- 服务器侧 DNS 查询未返回 `api.yeyubaka.top`；返回了 `new.api.yeyubaka.top -> 47.99.150.221`。本机 `api.yeyubaka.top` 的解析落到本地代理地址，不能作为公网 DNS 已生效的证据。
- `https://new.api.yeyubaka.top/` 当前返回 200；`https://api.yeyubaka.top/health` 当前 TLS 未建立成功。两者均只读验证，未作任何修复。

## 独立审查后的代码核对

独立审查员 Banach 只读复核了资源和部署风险；以下项目又在仓库中逐项核对，尚未修改实现：

- `backend\Dockerfile` 默认启动 4 个 worker；目标节点只有 2 vCPU，这不能作为生产默认值。
- `compose.override.yml` 是开发配置，包含宿主机 80/443 相关端口、Mailpit、Playwright 和 Traefik insecure API；`development.md` 明确说明 Compose 会自动加载 override。生产命令必须显式指定生产文件，不能直接运行默认合并结果。
- `backend\scripts\prestart.sh` 才执行 Alembic migration 和初始数据；当前 backend 的 Compose command/CMD 没有自动调用它，因此生产需要一次性迁移/初始化步骤。
- `/api/v1/utils/health-check/` 只返回固定 `true`，而真正检查 PostgreSQL、Redis 和迁移状态的 `/api/v1/health/ready` 没有接入当前 Compose backend healthcheck；发布前必须修正健康检查契约并在真实依赖上验证。
- Redis 当前使用 `--save "" --appendonly no`，且没有数据卷；重启会丢失缓存、限流计数及 lease/fencing 状态，生产策略必须明确接受或补充持久化/切换处理。
- 生产 Compose 没有显式传递 `FASTAPI_ENV`、`FRONTEND_HOST` 和正式 `API_PUBLIC_URL`；配置默认值仍可能是 `localhost`。正式环境必须显式注入并测试 OAuth、邮件链接和 CORS。
- 当前 `compose.yml` 使用可变的 `backend:latest`，也没有 CPU/内存上限、日志轮转和按 commit/digest 的回滚版本；不能把当前文件当作生产发布文件。
- backend 镜像 healthcheck 使用 `curl`，Dockerfile 没有显式安装 curl；是否由基础镜像提供尚未在实际 Linux 镜像中验证，不能把健康检查当前视为已通过。

## 当前判断

当前服务器不适合在不调整的情况下直接承载公开生产版。原因不是 Docker 缺失，而是现有服务已占用大部分可用内存，当前平台 Compose 栈还需要 PostgreSQL、Redis、应用、反向代理和独立数据/日志；应用镜像还包含多阶段前端构建，不能在 2 vCPU/3.4 GiB 节点上把在线构建当作常规发布路径。

它可以作为低流量、受控灰度候选，但必须先完成以下设计和用户确认：

1. 优先升级到至少 4 vCPU/8 GiB 内存，并保留至少 40 GiB 可用空间；否则只允许限流很严的实验性灰度，不应承诺稳定公益服务。
2. 在本机构建并推送已验证镜像，服务器只执行拉取/启动，避免在线多阶段构建抢占内存；Compose 发布必须使用独立项目名、目录、网络、数据库、Redis、日志和回滚版本。
3. 生产禁用或隔离 Adminer；为 backend、PostgreSQL、Redis、代理设置保守的 CPU/内存上限、日志轮转和健康检查，并预留 PostgreSQL 备份空间。
4. 不占用宿主机 80/443；由现有 Nginx 新增只匹配 `api.yeyubaka.top` 的独立 vhost，反代到独立本地端口。该变更必须先提交影响文件、验证步骤和回滚方案并等待确认。
5. DNS、证书、SMTP、GitHub OAuth 和生产 Secret 仍未验证；没有这些条件不能宣称上线。

结论：本次 Docker CLI 安装和服务器只读检查已完成；项目本身仍处于“不可发布/待验证”，不应直接在这台 2 vCPU/3.4 GiB 服务器上上线当前完整生产栈。
