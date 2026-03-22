# Immortal-Custom-Rules

自定义代理规则仓库，支持 Clash / mihomo / SingBox。

## 目录结构

```
├── ruleset/              # 代理规则集
│   ├── clash/           # Clash 规则 (list 格式)
│   └── singbox/         # SingBox 规则 (json 格式)
├── converted/           # 转换后的 MRS 格式规则
│   └── Loyalsoldier/    # 从 Loyalsoldier/clash-rules 转换
├── template/            # 路由器配置模板
│   └── router_*.yaml    # mihomo/OpenClash 配置
├── subscription/        # 订阅文件
├── shell/              # 构建脚本
├── pubic_dns_server_list.md  # 公共 DNS 服务器列表
└── config.json         # 配置文件
```

## 规则分类

| 文件 | 说明 |
|------|------|
| `proxy.list` / `proxy.json` | 代理规则 |
| `direct.list` / `direct.json` | 直连规则 |
| `reject.list` / `reject.json` | 广告/恶意域名拦截 |
| `download.list` / `download.json` | 下载相关规则 |

## 自动转换

项目使用 GitHub Actions 自动从 [Loyalsoldier/clash-rules](https://github.com/Loyalsoldier/clash-rules) 获取最新规则，通过 mihomo 转换为 MRS 格式。

转换后的规则文件保存在 `converted/Loyalsoldier/` 目录。

## 路由器配置

`template/` 目录提供 OpenClash 路由器配置模板，包含：
- 代理组配置
- 规则提供方配置
- DNS 配置
- 常规设置

## 使用方式

### Clash/mihomo

引用 `converted/Loyalsoldier/` 下的 `.mrs` 文件到配置中。

### OpenClash

使用 `template/` 目录下的模板进行配置。

## 相关项目

- [Loyalsoldier/clash-rules](https://github.com/Loyalsoldier/clash-rules)
- [MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo)
