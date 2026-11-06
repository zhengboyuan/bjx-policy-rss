# 北极星电力网政策 RSS

源栏目：<https://news.bjx.com.cn/zc/1/>

**当前状态：预览，非完整历史，尚未自动更新。** 2026-11-06 本机和 GitHub Actions 均被验证页阻挡。已从正常浏览器保存的公开首页生成 64 篇预览，栏目共 79 页。定时任务暂停，避免持续失败。

预览订阅：<https://raw.githubusercontent.com/zhengboyuan/bjx-policy-rss/main/public/feed.xml>

非官方订阅生成器。采集代码支持首次遍历当前公开分页，后续增量保存历史标题、发布日期及原文链接。预览不冒充完整归档；首次恢复抓取时会强制扫描所有分页。发布日期保留原日期，不伪造新日期。RSS 阅读器是否加载全部历史取决于阅读器。

抓取使用普通 HTTP 或标准 Playwright 浏览器；不处理滑动验证，不保存浏览器凭据。遇到访问验证、结构变化、分页重复或网络错误即失败，保留上一版数据。

```sh
pip install -r requirements.txt
python -m playwright install --with-deps chromium
python collect.py
python collect.py --full  # 重新扫描全部公开分页
```

可手动运行 GitHub Actions：`collect` 尝试采集后发布，`publish` 仅部署已核实的归档。恢复可靠访问后再启用定时采集。公开分页覆盖范围不等于网站创办以来的全部文章；正文请访问原文。
