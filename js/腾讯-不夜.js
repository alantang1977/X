const CryptoJS = require("crypto-js");

const base_host = "https://v.qq.com";
const header = {
  'User-Agent': 'PC_UA'
};

const _home = async ({ filter }) => {
  const homeUrl = '/x/bu/pagesheet/list?_all=1&append=1&channel=cartoon&listpage=1&offset=0&pagesize=21&iarea=-1&sort=18';
  const response = await fetch(`${base_host}${homeUrl}`, { headers: header });
  const html = await response.text();

  const videos = [];
  const listItems = html.match(/<div[^>]*class=["']?list_item["']?[^>]*>([\s\S]*?)<\/div>/gi) || [];

  for (const item of listItems) {
    const titleMatch = item.match(/<img[^>]*alt=["']?([^"']*)["']?/i);
    const picMatch = item.match(/<img[^>]*src=["']?([^"'\s>]+)["']?/i);
    const descMatch = item.match(/<a[^>]*>([\s\S]*?)<\/a>/i);
    const urlMatch = item.match(/<a[^>]*data-float=["']?([^"'\s>]+)["']?/i);

    if (titleMatch && picMatch) {
      videos.push({
        vod_id: urlMatch ? urlMatch[1] : '',
        vod_name: titleMatch[1] || '',
        vod_pic: picMatch[1] || '',
        vod_remarks: descMatch ? descMatch[1].replace(/<[^>]*>/g, '').trim() : ''
      });
    }
  }

  return {
    class: [
      { type_id: 'choice', type_name: '精选' },
      { type_id: 'movie', type_name: '电影' },
      { type_id: 'tv', type_name: '电视剧' },
      { type_id: 'variety', type_name: '综艺' },
      { type_id: 'cartoon', type_name: '动漫' },
      { type_id: 'child', type_name: '少儿' },
      { type_id: 'doco', type_name: '纪录片' }
    ],
    list: videos.slice(0, 20)
  };
};

const _category = async ({ id, page, filter, filters }) => {
  const offset = (parseInt(page) - 1) * 21;
  let url = `${base_host}/x/bu/pagesheet/list?_all=1&append=1&channel=${id}&listpage=1&offset=${offset}&pagesize=21&iarea=-1`;

  if (filters && filters.sort) {
    url += `&sort=${filters.sort}`;
  }
  if (filters && filters.iyear) {
    url += `&iyear=${filters.iyear}`;
  }
  if (filters && filters.year) {
    url += `&year=${filters.year}`;
  }
  if (filters && filters.type) {
    url += `&itype=${filters.type}`;
  }
  if (filters && filters.feature) {
    url += `&ifeature=${filters.feature}`;
  }
  if (filters && filters.area) {
    url += `&iarea=${filters.area}`;
  }
  if (filters && filters.itrailer) {
    url += `&itrailer=${filters.itrailer}`;
  }
  if (filters && filters.sex) {
    url += `&gender=${filters.sex}`;
  }

  const response = await fetch(url, { headers: header });
  const html = await response.text();

  const videos = [];
  const listItems = html.match(/<div[^>]*class=["']?list_item["']?[^>]*>([\s\S]*?)<\/div>/gi) || [];

  for (const item of listItems) {
    const titleMatch = item.match(/<img[^>]*alt=["']?([^"']*)["']?/i);
    const picMatch = item.match(/<img[^>]*src=["']?([^"'\s>]+)["']?/i);
    const descMatch = item.match(/<a[^>]*>([\s\S]*?)<\/a>/i);
    const urlMatch = item.match(/<a[^>]*data-float=["']?([^"'\s>]+)["']?/i);

    if (titleMatch && picMatch) {
      videos.push({
        vod_id: `${id}$${urlMatch ? urlMatch[1] : ''}`,
        vod_name: titleMatch[1] || '',
        vod_pic: picMatch[1] || '',
        vod_remarks: descMatch ? descMatch[1].replace(/<[^>]*>/g, '').trim() : ''
      });
    }
  }

  return {
    list: videos,
    page: parseInt(page),
    pagecount: 9999,
    limit: 21,
    total: 999999
  };
};

// ==========================================================
// 辅助函数：批量获取视频详情 (参考腾云驾雾逻辑)
// ==========================================================
const _getBatchVideoInfo = async (vids) => {
  const results = [];
  const batches = [];
  // 腾讯接口限制每次查询约30个ID，进行分批处理
  for (let i = 0; i < vids.length; i += 30) {
    batches.push(vids.slice(i, i + 30));
  }

  for (const batch of batches) {
    const url = `https://union.video.qq.com/fcgi-bin/data?otype=json&tid=1804&appid=20001238&appkey=6c03bbe9658448a4&union_platform=1&idlist=${batch.join(",")}`;
    try {
      const response = await fetch(url, { headers: header });
      const text = await response.text();
      // 清理 JSONP 格式: QZOutputJson={...}; -> {...}
      const jsonString = text.replace(/^QZOutputJson=/, '').replace(/;$/, '');
      const json = JSON.parse(jsonString);

      if (json.results) {
        json.results.forEach(item => {
          const fields = item.fields;
          results.push({
            vid: fields.vid,
            title: fields.title, // 原始标题
            // 判断类型：category_map[1] 通常存放 "正片", "预告", "花絮" 等
            type: fields.category_map && fields.category_map.length > 1 ? fields.category_map[1] : ""
          });
        });
      }
    } catch (e) {
      console.error('批量获取视频详情失败:', e);
    }
  }
  return results;
};

// ==========================================================
// 详情页逻辑修正：分离正片与花絮
// ==========================================================
const _detail = async ({ id }) => {
  const result = { list: [] };

  for (const id_ of id) {
    const [cid, sourceId] = id_.split('$');
    const targetCid = sourceId || cid;
    const detailUrl = `https://node.video.qq.com/x/api/float_vinfo2?cid=${targetCid}`;

    try {
      const response = await fetch(detailUrl, { headers: header });
      const json = await response.json();

      const vod = {
        vod_id: id_,
        vod_name: json.c?.title || '',
        type_name: json.typ?.join(",") || '',
        vod_actor: json.nam?.join(",") || '',
        vod_year: json.c?.year || '',
        vod_content: json.c?.description || '',
        vod_remarks: json.rec || '',
        vod_pic: json.c?.pic ? new URL(json.c.pic, base_host).href : '',
        vod_play_from: 'qq',
        vod_play_url: ''
      };

      const videoIds = json.c?.video_ids || [];

      if (videoIds.length > 0) {
        // 1. 获取详细列表信息（区分正片和花絮）
        const videoDetails = await _getBatchVideoInfo(videoIds);

        // 2. 映射排序：保证详情顺序与原始ID顺序一致
        const orderedDetails = videoIds.map(vid => {
          return videoDetails.find(v => v.vid === vid) || { vid: vid, title: '', type: '' };
        });

        // 3. 分组逻辑
        // 正片：类型为空(有些电影没tag)，或者类型为"正片"
        const zhengPian = orderedDetails.filter(it => !it.type || it.type === "正片");
        // 花絮/预告：类型存在且不为"正片"
        const yuGao = orderedDetails.filter(it => it.type && it.type !== "正片");

        // 4. 格式化播放地址
        const formatUrl = (items) => {
          return items.map(it => {
            let displayTitle = it.title ? it.title.trim() : ""; // 确保去除空格
            if (!displayTitle) displayTitle = "选集";
            if (/^\d+$/.test(displayTitle)) displayTitle = `第${displayTitle}集`;

            // 确保 URL 没有空格
            const playUrl = `${base_host}/x/cover/${targetCid}/${it.vid}.html`.trim();

            return `${displayTitle}$${playUrl}`;
          }).join('#');
        };

        const zhengPianUrls = formatUrl(zhengPian);
        const yuGaoUrls = formatUrl(yuGao);

        // 5. 组装最终输出
        // 如果没有花絮，则只显示一列；如果有，则用$$$分隔
        if (yuGao.length === 0) {
          vod.vod_play_from = "qq";
          // 如果正片列表也空(极少情况)，则使用全部列表兜底
          vod.vod_play_url = zhengPianUrls || formatUrl(orderedDetails);
        } else {
          // 如果正片为空（例如纯预告片页），只显示花絮
          if (!zhengPianUrls) {
            vod.vod_play_from = "qq_extra";
            vod.vod_play_url = yuGaoUrls;
          } else {
            vod.vod_play_from = "qq$$$qq_extra";
            vod.vod_play_url = `${zhengPianUrls}$$$${yuGaoUrls}`;
          }
        }
      }

      result.list.push(vod);
    } catch (error) {
      console.error('获取详情失败:', error);
    }
  }

  return result;
};

const _search = async ({ page, quick, wd }) => {
  const url = 'https://pbaccess.video.qq.com/trpc.videosearch.mobile_search.MultiTerminalSearch/MbSearch?vplatform=2';

  const headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.139 Safari/537.36',
    'Content-Type': 'application/json',
    'Origin': 'https://v.qq.com',
    'Referer': 'https://v.qq.com/'
  };

  const payload = {
    "version": "25042201",
    "clientType": 1,
    "filterValue": "",
    "uuid": "B1E50847-D25F-4C4B-BBA0-36F0093487F6",
    "retry": 0,
    "query": wd,
    "pagenum": parseInt(page) - 1,
    "isPrefetch": true,
    "pagesize": 30,
    "queryFrom": 0,
    "searchDatakey": "",
    "transInfo": "",
    "isneedQc": true,
    "preQid": "",
    "adClientInfo": "",
    "extraInfo": {
      "isNewMarkLabel": "1",
      "multi_terminal_pc": "1",
      "themeType": "1",
      "sugRelatedIds": "{}",
      "appVersion": ""
    }
  };

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(payload)
    });

    const json = await response.json();
    const videos = [];

    const processItem = (it) => {
      if (it && it.doc && it.doc.id && it.videoInfo) {
        if (it.doc.id.length > 11) {
          const cleanTitle = it.videoInfo.title ? it.videoInfo.title.replace(/<\/?em>/g, '') : '';
          videos.push({
            vod_id: it.doc.id,
            vod_name: cleanTitle,
            vod_pic: it.videoInfo.imgUrl || '',
            vod_remarks: it.videoInfo.firstLine || it.videoInfo.secondLine || ''
          });
        }
      }
    };

    if (json.data && json.data.normalList && json.data.normalList.itemList) {
      json.data.normalList.itemList.forEach(processItem);
    }

    if (json.data && json.data.areaBoxList && Array.isArray(json.data.areaBoxList)) {
      json.data.areaBoxList.forEach(area => {
        if (area.itemList) {
          area.itemList.forEach(processItem);
        }
      });
    }

    return {
      list: videos,
      page: parseInt(page),
      pagecount: videos.length >= 20 ? parseInt(page) + 1 : parseInt(page),
      limit: 30,
      total: 999
    };

  } catch (error) {
    console.error('搜索解析失败:', error);
    return {
      list: [],
      page: 1,
      pagecount: 1,
      limit: 30,
      total: 0
    };
  }
};

const _play = async ({ flag, flags, id }, app) => {
  const parses = [];
  try {
    // 'app' 预计是 req.server 对象, 它持有已注册的解析器
    parses.push(app.parse_fish); // parses目录下的fish.js
    parses.push(app.xmflv);
    // ... 可添加多个
  } catch {
    // 此处是防止添加不存在的解析造成的异常
  }

  for (const parse of parses) {
    if (!parse) continue; // 跳过未定义的解析器
    try {
      return await parse({ flag, flags, id });
    } catch (e) {
      // 检查 app.log 是否存在, 否则使用 console.error
      if (app && app.log) {
        app.log.error(`解析失败：${e.message}`);
      } else {
        console.error(`解析失败：${e.message}`);
      }
    }
  }

  //全部失败则返回给壳处理
  // 保留了原始的 header 和 jx: 1, parse: 1
  return {
    parse: 1,
    jx: 1,
    url: id,
    header: header
  };
};

const _proxy = async (req, reply) => {
  return Object.assign({}, req.query, req.params);
};

const meta = {
  key: "tengxun",
  name: "腾云驾雾",
  type: 4,
  api: "/video/tengxun",
  searchable: 2,
  quickSearch: 0,
  changeable: 0,
};

module.exports = async (app, opt) => {
  app.get(meta.api, async (req, reply) => {
    const { extend, filter, t, ac, pg, ext, ids, flag, play, wd, quick } = req.query;

    if (play) {
      return await _play({ flag: flag || "", flags: [], id: play }, req.server);
    } else if (wd) {
      return await _search({
        page: parseInt(pg || "1"),
        quick: quick || false,
        wd,
      });
    } else if (!ac) {
      return await _home({ filter: filter ?? false });
    } else if (ac === "detail") {
      if (t) {
        const body = {
          id: t,
          page: parseInt(pg || "1"),
          filter: filter || false,
          filters: {},
        };
        if (ext) {
          try {
            body.filters = JSON.parse(
              CryptoJS.enc.Base64.parse(ext).toString(CryptoJS.enc.Utf8)
            );
          } catch { }
        }
        return await _category(body);
      } else if (ids) {
        return await _detail({
          id: ids
            .split(",")
            .map((_id) => _id.trim())
            .filter(Boolean),
        });
      }
    }

    return req.query;
  });
  app.get(`${meta.api}/proxy`, _proxy);
  opt.sites.push(meta);
};