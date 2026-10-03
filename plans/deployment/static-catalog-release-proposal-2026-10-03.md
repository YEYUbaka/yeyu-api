# 静态 API 收集目录发布变更单（待用户确认）

日期：2026-10-03（Asia/Singapore）  
项目：`E:\AI_projects\yeyu-api`  
目标域名：`https://api.yeyubaka.top`  
发布类型：独立静态文件，不新增 Docker、数据库、缓存、动态 upstream、账号或 API 调用服务。

## 当前发布物

- 发布包：`E:\AI_projects\yeyu-api\deploy\packages\static-catalog-ce6eecb185015e637833a50be5e778059f6e776e.zip`
- 发布包对应 clean commit：`ce6eecb185015e637833a50be5e778059f6e776e`
- manifest 与 `build-meta.json` 的 commit、文件 SHA-256 已一致。
- 当前页面只收集第三方 API 资料和官方链接；浏览器端搜索/筛选，不向本项目后端或第三方上游发请求。

## 只读 preflight 结论

- 服务器为 2 vCPU、约 3.4 GiB 内存，80/443 已由现有 Nginx 监听。
- 现有服务继续占用若干回环端口；本项目不应新增容器或抢占 80/443。
- Docker 可用，但本发布不使用 Docker。
- `/opt/yeyu-api-static` 尚不存在。
- Nginx 当前加载 `/etc/nginx/conf.d/*.conf` 和 `/etc/nginx/sites-enabled/*`，没有 `api.yeyubaka.top` 配置。
- 当前公网 DNS/HTTPS 尚未形成可用证据：DoH 对 `api.yeyubaka.top` 返回 NXDOMAIN，本机网络解析还返回 `198.18.0.x` 保留测试网地址；TLS 探测失败。
- 完整证据：`E:\AI_projects\yeyu-api\plans\verification\server-preflight-2026-10-03.md`。

## 待确认的变更范围

### 1. DNS

为 `api.yeyubaka.top` 新增或修正仅属于该域名的公网 DNS 记录，指向执行 preflight 时确认的目标服务器地址。不会改动 `new.api.yeyubaka.top` 或其他域名记录。

影响：DNS TTL 生效期间，访问者可能看到旧的 NXDOMAIN/缓存结果；不涉及旧网站文件和现有容器。  
验证：使用权威 DNS、多个公共递归 DNS 和 HTTPS 解析结果核对。  
回滚：记录变更前的 DNS 状态；如验证失败，恢复变更前记录并等待 TTL 过期。

### 2. 静态文件目录

新增独立目录：

```text
/opt/yeyu-api-static/releases/ce6eecb185015e637833a50be5e778059f6e776e/
/opt/yeyu-api-static/current
```

`current` 只指向已上传并校验 SHA-256 的 release 目录；不使用 `/www/wwwroot/yeyubaka.top`，不使用 `new.api.yeyubaka.top` 的目录或容器。

影响：只新增本项目静态文件和发布指针。  
验证：远端核对目录属主、权限、文件清单、manifest SHA-256 和 `index.html`。  
回滚：将 `current` 原子切回上一个 release；如果首次发布失败，删除本项目新增目录，不触碰其他目录。

### 3. Nginx vhost

拟新增目标文件：

```text
/etc/nginx/sites-enabled/api.yeyubaka.top
```

配置只匹配 `server_name api.yeyubaka.top`，root 指向 `/opt/yeyu-api-static/current`，不包含 upstream、反代、代理抓取或动态 API 路由。HTTP/HTTPS 的证书文件路径必须在执行前单独确认，不复用 `new.api.yeyubaka.top` 的证书或配置。

影响：增加一个独立 vhost；不修改已有 Nginx vhost，不改变 80/443 listener，不重启或重建现有容器。  
验证：先做配置语法检查，再 reload；随后检查目标域名的 HTTPS、响应头、静态资源、移动端页面和不存在的动态路径。同步检查旧个人网站及 `new.api.yeyubaka.top` 仍可用。  
回滚：保存新增配置的版本和 checksum；验证失败时移除/恢复该新增 vhost，重新 `nginx -t` 后 reload；旧 vhost 不做覆盖式编辑。

### 4. 最小权限发布方式

发布账号、目录属主、Nginx reload 权限和证书申请方式目前均未在服务器上创建或修改。建议上传使用独立非 root 账号，系统级 Nginx/证书动作使用受控 sudo 白名单；不把 SSH 私钥、DNS Token 或证书私钥写入仓库、聊天或日志。

## 发布前阻塞项

在用户确认前不执行任何变更。即使用户确认发布范围，以下条件仍必须逐项满足后才能称为上线：

1. `api.yeyubaka.top` 权威 DNS 已指向目标服务器。
2. 已准备并验证只属于该域名的 HTTPS 证书。
3. 已确认非 root 发布账号和最小权限路径。
4. 上传包的 SHA-256 与本地 manifest 一致。
5. Nginx `-t`、reload、HTTPS、移动端和旧服务回归检查全部通过。

当前状态：只读 preflight 和本地发布包已完成；DNS、证书、服务器目录、发布账号、上传、Nginx 配置和线上验收均未执行。
