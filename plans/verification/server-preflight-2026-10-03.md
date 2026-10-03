# 静态目录服务器只读 preflight 证据

检查时间：2026-10-03 10:25（Asia/Singapore）  
候选服务器：已配置的 `yeyuhome` 只读 SSH 入口  
检查范围：CPU、内存、磁盘、inode、监听端口、Docker、Nginx、DNS、TLS 和独立目录状态。

本记录只覆盖只读命令。没有上传文件，没有创建目录，没有重载或修改 Nginx，没有修改 DNS，没有启动或停止容器，也没有访问旧个人网站仓库。

## 服务器资源

- 系统：Ubuntu 26.04 LTS，x86_64。
- CPU：2 vCPU。
- 内存：总计约 3.4 GiB；检查时 available 约 1.4 GiB；Swap 2 GiB，已用 0。
- 根分区：49 GiB，总已用约 21 GiB，可用约 26 GiB，使用率 45%。
- inode：使用率 16%。

## 现有服务与端口

- 宿主机 `0.0.0.0:80`、`0.0.0.0:443` 由现有 Nginx 监听。
- 现有容器通过本机回环地址使用 3000、5700、8000、8001 和 8080 等端口；没有为本项目预留的静态目录或监听端口。
- 当前运行容器包括 `meter-vision-web-1`、`meter-vision-backend-1`、`meter-vision-postgres-1`、`yatori-server`、`unified-ai-new-api` 和 `qinglong`。本次没有对它们执行操作。
- `/opt/yeyu-api-static` 不存在；未创建它。
- `/www/wwwroot/yeyubaka.top` 当前不存在；未创建、删除或修改该路径，也不能据此推断现有个人网站的真实根目录。

## Docker

- Docker Engine：29.1.3；Compose 插件：2.40.3。
- Docker 根目录：`/var/lib/docker`。
- 服务器有 2 vCPU、约 3.4 GiB 内存；Docker 当前 7 个容器（6 个运行中）。
- Docker 磁盘统计：镜像约 10.38 GiB，Build cache 约 7.98 GiB。
- Docker CLI 和 daemon 可用，但这不等于当前节点适合承载动态 API 平台。当前交付只需要静态文件，不应为本项目新增 Docker 服务。

## Nginx 与域名

- `nginx -t` 只读检查通过。
- 在已检查的 Nginx 配置目录中没有匹配 `server_name api.yeyubaka.top` 或 `server_name new.api.yeyubaka.top` 的目标配置行；现有 `new.api.yeyubaka.top` 不作为本项目入口，也不允许复用或改写。
- `api.yeyubaka.top` 当前没有可用 HTTPS：本机 `curl` TLS 握手失败。
- Cloudflare DoH 和 Google DoH 对 `api.yeyubaka.top` 返回 NXDOMAIN；本机/指定 DNS 查询又返回 `198.18.0.x` 保留测试网地址，属于当前网络解析环境信号，不能当作公网 A 记录已生效的证据。
- 服务器侧 `getent` 没有得到 `api.yeyubaka.top`；`new.api.yeyubaka.top` 仍解析到既有服务地址 `47.99.150.221`。本次没有请求或修改该既有服务。

## 判断

当前可以继续本地维护静态目录，也可以在用户批准后设计独立静态发布，但还不能宣称已上线。正式发布至少需要单独获批并验证：

1. DNS 只为 `api.yeyubaka.top` 配置正确的公网记录。
2. 在服务器独立目录 `/opt/yeyu-api-static/releases/<commit-sha>/` 上传静态包，并用 `current` 指针切换版本。
3. 新增只匹配 `api.yeyubaka.top` 的独立 Nginx vhost；不修改旧站点和 `new.api.yeyubaka.top`。
4. 以非 root 的最小权限发布账号完成上传/回滚；root 仅用于获批的系统级 Nginx/证书操作。
5. 先做 `nginx -t`，再执行可回滚的 reload，并验证新域名 HTTPS、桌面/移动端和旧服务不受影响。

在上述变更获批前，不执行 DNS、证书、服务器目录、Nginx、上传或 reload 操作。
