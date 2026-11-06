# 北极星电力网政策 RSS

源栏目：<https://news.bjx.com.cn/zc/1/>

非官方订阅生成器，首次遍历栏目当前公开分页，后续每 6 小时检查更新并持久保存历史标题、发布日期及原文链接。发布日期保留原日期，不伪造新日期。RSS 阅读器是否加载全部历史取决于阅读器。

抓取使用普通 HTTP 或标准 Playwright 浏览器；不处理滑动验证，不保存浏览器凭据。遇到访问验证、结构变化、分页重复或网络错误即失败，保留上一版数据。

```sh
pip install -r requirements.txt
python -m playwright install --with-deps chromium
python collect.py
python collect.py --full  # 重新扫描全部公开分页
```

首次云端采集成功后才会生成 `public/feed.xml`。公开分页覆盖范围不等于网站创办以来的全部文章；正文请访问原文。
