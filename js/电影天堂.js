const axios = require("axios");
const http = require("http");
const https = require("https");

const _http = axios.create({
  timeout: 15 * 1000,
  httpsAgent: new https.Agent({ keepAlive: true, rejectUnauthorized: false }),
  httpAgent: new http.Agent({ keepAlive: true }),
});

// 配置项：需要排除的分类名称
const excludeClassNames = ["海外动漫", "港台动漫"];

// 分类排序配置
const classSortOrder = [
  "国产剧", "欧美剧", "韩国剧", "日本剧", "泰国剧", "香港剧", "台湾剧", "海外剧",
  "剧情片", "动作片", "喜剧片", "爱情片", "科幻片", "恐怖片", "战争片", "动画片", "记录片", "伦理片",
  "国产动漫", "日韩动漫", "欧美动漫",
  "大陆综艺", "欧美综艺", "日韩综艺", "港台综艺",
  "短剧"
];

// 检查分类是否需要排除
const shouldExcludeClass = (typeName) => {
  if (!typeName) return false;
  return excludeClassNames.some(keyword => typeName && typeName.includes(keyword));
};

// 分类排序函数
const sortClasses = (classes) => {
  if (!classes || !Array.isArray(classes)) return classes;
  
  return classes.sort((a, b) => {
    const nameA = a.type_name || "";
    const nameB = b.type_name || "";
    const indexA = classSortOrder.indexOf(nameA);
    const indexB = classSortOrder.indexOf(nameB);
    if (indexA !== -1 && indexB !== -1) return indexA - indexB;
    if (indexA !== -1) return -1;
    if (indexB !== -1) return 1;
    return nameA.localeCompare(nameB, 'zh-CN');
  });
};

const fetch = async (req) => {
  delete req.query["token"];
  const { flag, play } = req.query;
  
  // 1. 如果是直接的播放文件地址，直接返回
  if (
    play &&
    /\.(m3u8|mp4|rmvb|avi|wmv|flv|mkv|webm|mov|m3u)(?!\w)/i.test(play)
  ) {
    return {
      url: play,
      jx: 0,
      parse: 0,
    };
  }

  // 2. 处理播放请求的代理 (保留原逻辑，用于去广告)
  if (req.query.ac === "videourl" || req.query.ac === "play") {
    const pid = req.query.id || req.query.url;
    if (pid) {
      return {
        // 注意：这里使用了本地代理端口9978，确保你的APP支持此端口
        url: "http://127.0.0.1:9978/proxy?do=js&url=" + encodeURIComponent(pid),
        parse: 0,
        jx: 0,
        header: { 'User-Agent': 'okhttp/5.0.0' }
      };
    }
  }

  try {
    // --- 新增：构建纯净的参数对象 ---
    const params = {
      ac: req.query.ac,
    };
    // 只添加有值的必要参数，排除无关参数干扰搜索
    if (req.query.wd) params.wd = req.query.wd;
    if (req.query.pg) params.pg = req.query.pg;
    if (req.query.ids) params.ids = req.query.ids;
    if (req.query.t) params.t = req.query.t;
    // ----------------------------

    const ret = await _http("", {
      params: params, // 使用清理后的 params
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.95 Safari/537.36',
      },
      baseURL: "http://caiji.dyttzyapi.com/api.php/provide/vod/from/dyttm3u8/at/json/",
    });
    
    const data = ret.data || {};
    
    // 3. 首页分类
    if (req.query.ac === "list" && !req.query.wd) {
      const excludeTypeIds = [1, 2, 3, 4, 5];
      const return_data = {
        class: []
      };
      
      if (data.class && Array.isArray(data.class)) {
        const filteredClasses = [];
        data.class.forEach((i) => {
          if (excludeTypeIds.includes(i.type_id)) return;
          if (shouldExcludeClass(i.type_name)) return;
          filteredClasses.push({
            type_id: i.type_id?.toString() || '',
            type_name: i.type_name || ''
          });
        });
        return_data.class = sortClasses(filteredClasses);
      }
      return return_data;
    }
    
    // 4. 分类列表/搜索/详情
    if (req.query.ac === "detail" || req.query.wd) {
      const return_data = {
        list: [],
        page: parseInt(req.query.pg) || 1,
        pagecount: data.pagecount || 1,
        limit: data.limit || 20,
        total: data.total || 0,
        parse: 0,
        jx: 0
      };
      
      const movieList = data.list || [];
      
      movieList.forEach(function (i) {
        if (!i) return;
        if (shouldExcludeClass(i.type_name)) return;
        
        if (req.query.ids) {
          // --- 详情页数据修复重点 ---
          return_data.list.push({
            type_name: i.type_name || '',
            vod_id: i.vod_id || '',
            vod_name: i.vod_name || '',
            vod_remarks: i.vod_remarks || '',
            vod_year: i.vod_year || '',
            vod_area: i.vod_area || '',
            vod_actor: i.vod_actor || '',
            vod_director: i.vod_director || '',
            vod_content: i.vod_content || '',
            vod_play_from: '',
            // 修复点：获取API返回的播放源名称，而不是传空字符串
            vod_play_from: i.vod_play_from || '',
            vod_play_url: i.vod_play_url || ''
          });
        } else {
          // 列表/搜索结果
          return_data.list.push({
            vod_id: i.vod_id || '',
            vod_name: i.vod_name || '',
            vod_pic: i.vod_pic || '',
            vod_remarks: i.vod_remarks || '',
            vod_year: i.vod_year || '',
            type_name: i.type_name || '',
          });
        }
      });
      
      return_data.total = return_data.list.length;
      return return_data;
    }
    
    return data;
  } catch (error) {
    console.error("Fetch error:", error.message);
    // 错误处理
    if (req.query.ac === "list") return { class: [] };
    if (req.query.ac === "detail") return { list: [], page: 1, pagecount: 1, limit: 20, total: 0 };
    return { error: error.message };
  }
};

// 广告过滤函数 (保持不变)
async function del_ads(url) {
  const url1 = url.replace('index.m3u8', '');
  const response = await axios.get(url, {
    headers: { 'User-Agent': 'okhttp/5.0.0' }
  });
  
  let text = response.data.trim().split('\n');
  let url2 = url1 + text[text.length - 1];
  let root_url = url2.replace('mixed.m3u8', '');
  
  const res2 = await axios.get(url2, {
    headers: { 'User-Agent': 'okhttp/5.0.0' }
  });
  
  return res2.data
    .replace(/#EXT-X-DISCONTINUITY\n((.*?\n){1,10})#EXT-X-DISCONTINUITY\n/g, '')
    .replace(/#EXT-X-DISCONTINUITY\n((.*?\n){2})#EXT-X-ENDLIST\n/g, '#EXT-X-ENDLIST')
    .replace(/#EXT-X-DISCONTINUITY\n/g, '')
    .replace(/(.*\.ts.*)/g, root_url + '$1');
}

const meta = {
  key: "dytt", 
  name: "电影天堂",
  type: 4,
  api: "/video/dytt", 
  ext: {
    desc: "已修复线路资源显示",
  }
};

module.exports = async (app, opt) => {
  app.get(meta.api, async (req, reply) => {
    const { extend, filter, t, ac, pg, ext, ids, flag, play, wd, quick } = req.query;
    
    // 路由参数适配
    if (play) {
      req.query.ac = "play";
      req.query.id = play;
    } else if (wd) {
      req.query.ac = "detail";
      req.query.wd = wd;
      req.query.pg = pg;
    } else if (!ac) {
      req.query.ac = "list";
    } else if (ac === "detail") {
      if (t) {
        req.query.ac = "detail";
        req.query.t = t;
        req.query.pg = pg;
      } else if (ids) {
        req.query.ac = "detail";
        req.query.ids = ids;
      }
    }
    
    try {
      return await fetch(req);
    } catch (error) {
      return { list: [] };
    }
  });
  
  opt.sites.push(meta);
  
  // 代理路由
  app.get("/dytt/proxy", async (req, res) => {
    const url = req.query.url;
    if (!url) return res.status(400).send("缺少URL参数");
    try {
      const result = await del_ads(url);
      res.header("Content-Type", "application/vnd.apple.mpegurl");
      res.send(result);
    } catch (error) {
      res.status(500).send("处理失败");
    }
  });
};
