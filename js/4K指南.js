var rule = {
    title: '4K指南',
    host: 'https://4kzn.com',
    url: '/books/fyclass',
    searchUrl: '/?post_type=book&s=**',
    searchable: 2,
    quickSearch: 0,
    headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    },
    timeout: 10000,
    class_name: '最新电影&最新剧集&系列合集&豆瓣TOP250',
    class_url: 'zuixin&zuixin-juji&xiliehj&top250',
    play_parse: true,
    lazy: $js.toString(() => {
        let url = input.startsWith('push://') ? input : 'push://' + input;
        input = {parse: 0, url: url};
    }),
    
    // 一级：首页列表
    一级: '.posts-item.book-item;.item-title&&Text;.item-image img&&data-src;.line1.text-muted.text-xs.mt-1&&Text;a&&href',
    
    // 二级：详情页
    二级: {
        "title": "h1&&Text||.item-title&&Text",
        "img": ".item-image img&&src||.item-image img&&data-src",
        "desc": ".line1.text-muted.text-xs.mt-1&&Text",
        "content": ".panel-body p&&Text||.item-body&&Text",
        "tabs": "js:TABS=['播放地址']",
        "lists": ".site-go a||.post-content a:contains(夸克)||.post-content a:contains(阿里)",
        "list_text": "a&&Text",
        "list_url": "a&&href"
    },
    
    // 搜索：搜索结果列表
    搜索: '.posts-item.book-item;.item-title&&Text;.item-image img&&data-src;.line1.text-muted.text-xs.mt-1&&Text;a&&href',
    
    // 预处理：修复懒加载图片
    preRule: $js.toString(() => {
        try {
            const html = typeof(input) === 'string' ? input : input.html;
            if (html) {
                // 修复懒加载图片
                const fixed = html.replace(/data-src=/g, 'src=');
                return { html: fixed };
            }
        } catch(e) {}
        return input;
    })
};
