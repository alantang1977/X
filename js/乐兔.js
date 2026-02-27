const CryptoJS = require("crypto-js");
const axios = require("axios");
const http = require("http");
const https = require("https");
const cheerio = require("cheerio");

const _http = axios.create({
  timeout: 60 * 1000,
  httpsAgent: new https.Agent({ keepAlive: true, rejectUnauthorized: false }),
  httpAgent: new http.Agent({ keepAlive: true }),
});

// 乐兔配置
const letuConfig = {
  host: "https://www.letu.me",
  headers: {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
    "Referer": "https://www.letu.me/"
  }
};

const PAGE_LIMIT = 20;

// 分类配置
const getClasses = () => {
  return [
    { type_id: "1", type_name: "电影" },
    { type_id: "2", type_name: "电视剧" },
    { type_id: "3", type_name: "综艺" },
    { type_id: "4", type_name: "动漫" },
    { type_id: "5", type_name: "短剧" }
  ];
};

const getFilters = () => {
  return {};
};

// 获取分类列表
const getCategoryList = async (type, page = 1, extend = {}) => {
  try {
    const tid = type || "1";
    const pg = page || 1;
    const url = `${letuConfig.host}/vodtype/${tid}-${pg}.html`;
    
    const response = await _http.get(url, { headers: letuConfig.headers });
    const $ = cheerio.load(response.data);
    const list = [];

    $(".grid.container_list .s6").each((_, element) => {
      const $el = $(element);
      const $link = $el.find("a");
      
      const name = $link.attr("title") || "";
      const href = $link.attr("href") || "";
      const pic = $el.find(".large").attr("data-src") || "";
      const remark = $el.find(".small-text").text().trim() || "";
      
      if (name && href) {
        list.push({
          vod_id: href,
          vod_name: name,
          vod_pic: pic.startsWith("http") ? pic : letuConfig.host + pic,
          vod_remarks: remark
        });
      }
    });

    return {
      list: list,
      page: parseInt(pg),
      pagecount: 999,
      limit: PAGE_LIMIT,
      total: 999 * PAGE_LIMIT
    };
  } catch (error) {
    store.log.error(error);
    return { list: [], page: 1, pagecount: 1, limit: PAGE_LIMIT, total: 0 };
  }
};

// 获取详情
const getDetail = async (id) => {
  try {
    const url = id.startsWith("http") ? id : letuConfig.host + id;
    const response = await _http.get(url, { headers: letuConfig.headers });
    const $ = cheerio.load(response.data);

    const vod_name = $("h1").first().text().trim();
    const vod_pic = $("img").first().attr("src") || "";
    const vod_type = $(".scroll.no-margin a").eq(0).text().trim();
    const vod_actor = $(".scroll.no-margin a").eq(1).text().trim();
    const vod_director = $(".no-space.no-margin.m.l").text().trim();
    const vod_area = $(".no-margin.m.l").text().trim();
    const vod_content = $(".responsive p").last().text().trim();

    // 解析播放列表
    const playFromList = [];
    const playUrlList = [];

    $(".tabs.left-align a").each((index, element) => {
      const tabName = $(element).text().trim();
      playFromList.push(tabName);

      const episodes = [];
      $(`.playno:eq(${index}) a`).each((_, ep) => {
        const epName = $(ep).text().trim();
        const epUrl = $(ep).attr("href") || "";
        if (epName && epUrl) {
          episodes.push(`${epName}$${epUrl}`);
        }
      });
      playUrlList.push(episodes.join("#"));
    });

    return {
      vod_id: id,
      vod_name: vod_name,
      vod_pic: vod_pic.startsWith("http") ? vod_pic : letuConfig.host + vod_pic,
      vod_type: vod_type,
      vod_actor: vod_actor,
      vod_director: vod_director,
      vod_area: vod_area,
      vod_content: vod_content,
      vod_play_from: playFromList.join("$$$"),
      vod_play_url: playUrlList.join("$$$")
    };
  } catch (error) {
    store.log.error(error);
    return null;
  }
};

// 播放解析
const getPlay = async (playUrl) => {
  try {
    const url = playUrl.startsWith("http") ? playUrl : letuConfig.host + playUrl;
    const response = await _http.get(url, { headers: letuConfig.headers });
    const html = response.data;

    // 尝试JSON接口解析
    try {
      const json = JSON.parse(html);
      if (json && json.code == 200 && json.url) {
        let videoUrl = json.url;

        // 处理Base64编码 (rose_开头)
        if (videoUrl.startsWith('rose_')) {
          const base64Part = videoUrl.substring(5);
          try {
            const decodedBase64 = decodeURIComponent(base64Part);
            videoUrl = Buffer.from(decodedBase64, 'base64').toString();
          } catch (e) {
            try {
              videoUrl = Buffer.from(base64Part, 'base64').toString();
            } catch (e2) {}
          }
        }
        // 处理相对路径
        else if (videoUrl.startsWith('/')) {
          videoUrl = letuConfig.host + videoUrl;
        }

        return {
          parse: 0,
          url: videoUrl,
          header: letuConfig.headers
        };
      }
    } catch (e) {}

    // MacCMS player配置解析
    try {
      const match = html.match(/player_.*?=(\{[\s\S]*?\})/);
      if (match) {
        const conf = JSON.parse(match[1].replace(/'/g, '"'));
        let videoUrl = conf.url || '';
        
        if (conf.encrypt == '1') videoUrl = decodeURIComponent(videoUrl);
        if (conf.encrypt == '2') videoUrl = Buffer.from(decodeURIComponent(videoUrl), 'base64').toString();
        
        if (videoUrl) {
          return {
            parse: 0,
            url: videoUrl,
            header: letuConfig.headers
          };
        }
      }
    } catch (e) {}

    // 兜底使用系统解析
    return {
      parse: 1,
      url: url,
      header: letuConfig.headers
    };
  } catch (error) {
    store.log.error(error);
    return {
      parse: 1,
      url: playUrl,
      header: letuConfig.headers
    };
  }
};

// 搜索功能
const getSearch = async (keyword, page = 1) => {
  try {
    const pg = page || 1;
    const url = `${letuConfig.host}/vodsearch/${keyword}----------${pg}---/`;
    
    const response = await _http.get(url, { headers: letuConfig.headers });
    const $ = cheerio.load(response.data);
    const list = [];

    $(".grid.container_list .s6").each((_, element) => {
      const $el = $(element);
      const $link = $el.find("a");
      
      const name = $link.attr("title") || "";
      const href = $link.attr("href") || "";
      const pic = $el.find(".large").attr("data-src") || "";
      const remark = $el.find(".small-text").text().trim() || "";
      
      if (name && href) {
        list.push({
          vod_id: href,
          vod_name: name,
          vod_pic: pic.startsWith("http") ? pic : letuConfig.host + pic,
          vod_remarks: remark
        });
      }
    });

    return {
      list: list,
      page: parseInt(pg),
      pagecount: 999,
      limit: PAGE_LIMIT,
      total: 999 * PAGE_LIMIT
    };
  } catch (error) {
    store.log.error(error);
    return { list: [], page: 1, pagecount: 1, limit: PAGE_LIMIT, total: 0 };
  }
};

// 处理T4请求
const handleT4Request = async (req) => {
  const { ac, t, pg, ids, wd, play, ext } = req.query;

  // 播放解析
  if (play) {
    return await getPlay(play);
  }

  // 详情页
  if (ids) {
    const detail = await getDetail(ids);
    return {
      list: detail ? [detail] : [],
      page: 1,
      pagecount: 1,
      total: detail ? 1 : 0
    };
  }

  // 搜索
  if (wd) {
    return await getSearch(wd, pg);
  }

  // 分类列表
  if (t !== undefined) {
    let extendParams = {};
    if (ext) {
      try {
        extendParams = JSON.parse(
          CryptoJS.enc.Base64.parse(ext).toString(CryptoJS.enc.Utf8)
        );
      } catch (e) {
        req.server.log.error(e);
      }
    }
    return await getCategoryList(t, pg, extendParams);
  }

  // 首页/分类
  if (!ac || ac === 'class') {
    const classes = getClasses();
    if (ac === 'class') return { class: classes };

    const result = await getCategoryList("1", 1);
    return {
      class: classes,
      filters: getFilters(),
      list: result.list,
      page: 1,
      pagecount: result.pagecount,
      total: result.total
    };
  }

  return { list: [], page: 1, pagecount: 1, limit: PAGE_LIMIT, total: 0 };
};

// 元数据
const meta = {
  key: "letu",
  name: "乐兔[采]",
  type: 4,
  api: "/video/letu",
  searchable: 1,
  quickSearch: 1,
  filterable: 0
};

const store = {
  init: false,
};

const init = async (server) => {
  if (store.init) return;
  store.log = server.log;
  store.init = true;
};

module.exports = async (app, opt) => {
  app.get(meta.api, async (req, reply) => {
    if (!store.init) {
      await init(req.server);
    }
    try {
      return await handleT4Request(req);
    } catch (error) {
      console.error(error);
      return { error: 'Internal Server Error' };
    }
  });
  opt.sites.push(meta);
};