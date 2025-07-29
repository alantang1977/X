var rule = {
  title: '4K极狐',
  host: 'https://4kfox.com',
  url: '/list/fyclass.html',
  searchUrl: '/search/-------------.html?wd=**&submit=',
  searchable: 2,
  quickSearch: 0,
  headers: { 'User-Agent': 'PC_UA' },
  timeout: 8000,
  class_name: '电影&剧集&动漫',
  class_url: 'dianying&juji&dongman',
  play_parse: true,
  lazy: $js.toString(() => {
      //推送阿里播放  支持影视壳
      let url = input.startsWith('push://') ? input : 'push://' + input;
      input = {parse: 0, url: url};
  }),
  /* 一级列表 */
  一级: '.hl-item-thumb;a&&title;a&&data-original;;a&&href',

  /* 二级：只抓网盘源，去掉“复制链接”字样，屏蔽在线源和磁力源 */
  二级: $js.toString(() => {
    let html = getHtml(input);
    let $ = cheerio.load(html);

    let vod = {
      vod_id: input,
      vod_name: $('.hl-dc-title').text().trim(),
      vod_pic: $('.hl-item-thumb').attr('data-original'),
      vod_remarks: $('.hl-vod-data li').eq(0).text().trim(),
      vod_content: $('.hl-content-text').text().trim()
    };

    /* 1. 线路名：只取网盘源所在的按钮文本 */
    let tabs = [];
    let lists = [];

    $('.hl-tabs-btn[alt]').each((i, e) => {
      let tabName = $(e).attr('alt');
      // 跳过在线源和磁力源
      if (/天堂源|暴风源|非凡源|量子源|如意源|720P|1080P|中字1080P|4K|中字4K|原盘|未知/i.test(tabName)) return;

      tabs.push(tabName);

      /* 2. 该线路下的所有 <li>，去掉“复制链接”字样，只留真实地址 */
      let items = [];
      $('.hl-tabs-box').eq(i).find('.hl-downs-list li').each((j, li) => {
        let a = $(li).find('a.down-name');
        let name = a.find('.filename').text().trim();   // 片名+清晰度
        let url  = a.attr('href');
        if (name && url) items.push(name + '$' + url);
      });
      lists.push(items.join('#'));
    });

    vod.vod_play_from = tabs.join('$$$');
    vod.vod_play_url  = lists.join('$$$');

    VOD = vod;
  }),

  /* 搜索列表 */
  搜索: '.hl-item-thumb;a&&title;a&&data-original;;a&&href'
};