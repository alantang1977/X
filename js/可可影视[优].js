/*
@header({
  searchable: 2,
  filterable: 1,
  quickSearch: 0,
  title: '可可影视[优]',
  '类型': '影视',
  lang: 'dr2'
})
*/

var rule = {
    title: '可可影视[优]',
    host: 'https://www.keke1.app',
    //host: 'https://www.kkys01.com',
    url: '/show/fyclass-----2-fypage.html',
    //url: '/show/fyclass-fyfilter-fypage.html',
    searchUrl: '/search?t=lw%2FzDeVGGBRTbdH2HVvs7Q%3D%3D&k=**&page=fypage',
    searchable: 2,
    quickSearch: 0,
    filterable: 1,
    headers: {
        'User-Agent': 'MOBILE_UA',
    },
    class_parse: '#nav-swiper&&.nav-swiper-slide;a&&Text;a&&href;/(\\w+).html',
    cate_exclude: 'Netflix|今日更新|专题列表|排行榜',
    tab_exclude:'可可影视提供',
    tab_order: ['超清', '蓝光', '极速蓝光'],
    tab_remove:['4K(高峰不卡)'],
    play_parse: true,
    lazy: $js.toString(() => {
        input = {
            parse: 1,
            url: input,
            js: 'document.querySelector("#my-video video").click()',
        }
    }),
    limit: 20,
    推荐: '.section-box:eq(2)&&.module-box-inner&&.module-item;*;*;*;*',
    double: false,
    一级: '.module-box-inner&&.module-item;.v-item-title:eq(1)&&Text;img:last-of-type&&data-original;.v-item-bottom&&span&&Text;a&&href',
    二级: {
        title: '.detail-pic&&img&&alt;.detail-tags&&a&&Text',
        img: '.detail-pic&&img&&data-original',
        desc: '.detail-info-row-main:eq(-2)&&Text;.detail-tags&&a&&Text;.detail-tags&&a:eq(1)&&Text;.detail-info-row-main:eq(1)&&Text;.detail-info-row-main&&Text',
        content: '.detail-desc&&Text',
        tabs: '.source-item-label',
        //tabs: 'body&&.source-item-label[id]',
        lists: '.episode-list:eq(#id) a',
    },
    搜索: '.search-result-list&&a;.title:eq(0)&&Text;.search-result-item-pic&&img&&data-original;.search-result-item-header&&Text;a&&href;.desc&&Text',
    图片替换:'https://www.keke1.app=>https://vres.zclmjc.com',
    预处理: $js.toString(() => {
        function extractHashFromResponse(ruleHost) {
            try {
                let response = request(ruleHost);
                const regex = /a0_0x2a54\s*=\s*\['([^']+)'/;
                let match = response.match(regex);
                return match ? match[1] : '';
            } catch (error) {
                console.error('请求失败:', error);
                return '';
            }
        }

        function sha1ToUint8ArrayLatin1(input) {
            let hash = CryptoJS.SHA1(input);
            let latin1String = hash.toString(CryptoJS.enc.Latin1);
            let uint8Array = new Uint8Array(latin1String.length);

            for (let i = 0; i < latin1String.length; i++) {
                uint8Array[i] = latin1String.charCodeAt(i);
            }

            return uint8Array;
        }

        function run(c, n1) {
            let i = 0;
            while (i < 1000000) {
                let input = c + i;
                let hash = sha1ToUint8ArrayLatin1(input);
                if (hash[n1] === 0xb0 && hash[n1 + 1] === 0x0b) {
                    let myck = 'cdndefend_js_cookie=' + c + i;
                    console.log('找到 myck:', myck);
                    rule.headers['cookie'] = myck;
                    setItem('mycookie', myck);
                    setItem('myhash', c);
                    break;
                }
                i++;
            }
            console.log('未找到符合条件的 i');
        }

        let hash = extractHashFromResponse(rule.host);
        if (hash != '' && hash != getItem('myhash')) {
            setItem('mycookie', '');
            setItem('myhash', '');
            run(hash, parseInt('0x' + hash[0], 16));
        }
        if (getItem('mycookie')) {
            rule.headers['cookie'] = getItem('mycookie');
        }

        let html = fetch(HOST, {headers: rule.headers});
        const regex2 = /<input type="hidden" name="t" value="([^"]+)"/;
        let match2 = html.match(regex2);
        rule.searchUrl = rule.searchUrl.replace("lw%2FzDeVGGBRTbdH2HVvs7Q%3D%3D", match2 ? encodeURIComponent(match2[1]) : '');
    }),
}