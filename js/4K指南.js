var rule = {
    title: 'xuexizhinan',
    host: 'https://4kzn.com/',
    url: '/books/fyclass',
    searchUrl: '/?post_type=book&s=**',
    searchable: 2,
    quickSearch: 0,
    headers: {
        'User-Agent': 'PC_UA',
    },
    timeout: 8000,
    class_name: '电影&剧集',
    class_url: 'zuixin&zuixin-juji',
    play_parse: true,
    lazy: $js.toString(() => {
        //推送阿里播放  支持影视壳
        let url = input.startsWith('push://') ? input : 'push://' + input;
        input = {parse: 0, url: url};
    }),
    一级: '.card-book.list-item;.list-title&&Text;a.media-content&&data-bg&&url\\s*[\\(\\（](.*?)[\\)\\）]/$1/;;a.list-title&&href',
    二级: {
        "title": ".rounded.shadow&&title",
        "img": ".rounded.shadow&&src",
        "desc": ";;;;",
        "content": ".panel-body p&&Text",
        "tabs": "js:TABS=['xuexizhinan']",
        "lists": ".site-go a",
        "list_text": "a:eq(0)&&Text",
        "list_url": "a:eq(0)&&href"
    },
    搜索: '.card-book.list-item;.list-title&&Text;a.media-content&&data-bg&&url\\s*[\\(\\（](.*?)[\\)\\）]/$1/;;a.list-title&&href'
};