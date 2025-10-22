// ==UserScript==
// @name         yfsp
// @namespace    gmspider
// @version      2024.11.12
// @description  爱壹帆 GMSpider
// @author       Luomo
// @match        https://m.yfsp.tv/*
// @require      https://cdn.jsdelivr.net/gh/CatVodSpider-GM/Spiders-Lib@main/lib/browser-extension-url-match-1.2.0.min.js
// @require      https://cdn.jsdelivr.net/npm/ajax-hook@3.0.3/dist/ajaxhook.umd.min.js
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        unsafeWindow
// @run-at       document-start
// ==/UserScript==
console.log(JSON.stringify(GM_info));
(function () {
    const GMSpiderArgs = {};
    if (typeof GmSpiderInject !== 'undefined') {
        let args = JSON.parse(GmSpiderInject.GetSpiderArgs());
        GMSpiderArgs.fName = args.shift();
        GMSpiderArgs.fArgs = args;
    } else {
        // GMSpiderArgs.fName = "homeContent";
        // GMSpiderArgs.fArgs = [true];
        // GMSpiderArgs.fName = "categoryContent";
        // GMSpiderArgs.fArgs = ["movie", 2, true, {}];
        // GMSpiderArgs.fName = "detailContent";
        // GMSpiderArgs.fArgs = [["XOkJ0XqSwI2"]];
        GMSpiderArgs.fName = "searchContent";
        GMSpiderArgs.fArgs = ["小巷人家", false, 1];
    }
    Object.freeze(GMSpiderArgs);
    (function () {
        switch (GMSpiderArgs.fName) {
            case "searchContent":
                localStorage.setItem("historyList", JSON.stringify([GMSpiderArgs.fArgs [0]]));
                break;
        }
    })();
    let hookConfigs = {
        "homeContent": [{
            dataKey: "navigationbar",
            matcher: matchPattern("https://*.yfsp.tv/api/list/navigationbar?*").assertValid()
        }, {
            dataKey: "index",
            matcher: matchPattern("https://*.yfsp.tv/api/list/index?*").assertValid()
        }],
        "categoryContent": [{
            dataKey: "filtertagsdata",
            matcher: matchPattern("https://*.yfsp.tv/api/list/getfiltertagsdata?*").assertValid()
        }, {
            dataKey: "conditionfilterdata",
            matcher: matchPattern("https://*.yfsp.tv/api/list/getconditionfilterdata?*").assertValid(),
            onRequestHook: function (config, handler) {
                let url = new URL(config.url);
                url.searchParams.set('page', GMSpiderArgs.fArgs[1]);
                config.url = url.toString();
            }
        }],
        "detailContent": [{
            dataKey: "videodetails",
            matcher: matchPattern("https://*.yfsp.tv/api/video/videodetails?*").assertValid()
        }, {
            dataKey: "playdata",
            matcher: matchPattern("https://*.yfsp.tv/api/video/getplaydata?*").assertValid()
        }, {
            dataKey: "videochoosegather",
            require: false,
            matcher: matchPattern("https://*.yfsp.tv/api/video/videochoosegather?*").assertValid()
        }],
        "playerContent": [{
            dataKey: "playdata",
            matcher: matchPattern("https://*.yfsp.tv/api/video/getplaydata?*").assertValid()
        }],
        "searchContent": [{
            dataKey: "titlegetdata",
            matcher: matchPattern("https://*.yfsp.tv/api/list/gettitlegetdata?*").assertValid()
        }, {
            matcher: matchPattern("https://*.yfsp.tv/api/home/gethotsearch?*").assertValid(),
            onResponseHook: function (response, handler) {
                document.querySelector(".search-log span").dispatchEvent(new Event("click"));
            }
        }],
    };
    const GmSpider = (function () {
        const categoryFilterCachePrefix = "category.";
        return {
            homeContent: function (filter) {
                let result = {
                    class: [],
                    filters: {},
                    list: []
                };
                let categoryIds = [];
                hookResult.navigationbar.data.list.forEach((item) => {
                    if (item.type === 1) {
                        result.class.push({
                            type_id: item.routeName,
                            type_name: item.name
                        });
                        categoryIds.push(item.categoryId);
                        // const cacheFilter = GM_getValue(item.routeName);
                        // console.log("cacheFilter", item.routeName, cacheFilter);
                        const cacheFilter = localStorage.getItem(categoryFilterCachePrefix + item.routeName);
                        console.log("localStorage", item.routeName, localStorage.getItem(item.routeName));
                        if (typeof cacheFilter !== "undefined" && cacheFilter !== null) {
                            result.filters[item.routeName] = JSON.parse(cacheFilter);
                        }
                    }

                })
                hookResult.index.data.list.forEach((item) => {
                    if (categoryIds.includes(item.type)) {
                        item.list.forEach((media) => {
                            if (!media.isRecommend) {
                                result.list.push({
                                    vod_id: media.mediaKey,
                                    vod_name: media.title,
                                    vod_pic: media.coverImgUrl,
                                    vod_remarks: media.updateStatus,
                                    vod_year: media.mediaType
                                })
                            }
                        })
                    }
                })
                return result;
            },
            categoryContent: function (tid, pg, filter, extend) {
                let result = {
                    list: [],
                    pagecount: 1000
                };
                let cacheFilters = [];
                hookResult.filtertagsdata.data.list.forEach(classify => {
                    let cacheFilter = {
                        key: "index-" + classify.list[0].index,
                        name: classify.name,
                        value: []
                    }
                    classify.list.forEach((item) => {
                        cacheFilter.value.push({
                            n: item.classifyName,
                            v: (item.index > 0 ? "," : "") + item.classifyId
                        });
                    })
                    cacheFilters.push(cacheFilter);
                })
                // GM_setValue(tid, JSON.stringify(cacheFilters));
                localStorage.setItem(categoryFilterCachePrefix + tid, JSON.stringify(cacheFilters));
                console.log("cacheFilter", tid, cacheFilters);
                hookResult.conditionfilterdata.data.list.forEach((media) => {
                    result.list.push({
                        vod_id: media.mediaKey,
                        vod_name: media.title,
                        vod_pic: media.coverImgUrl,
                        vod_remarks: media.updateStatus,
                        vod_year: media.regional
                    })
                })
                return result;
            },
            detailContent: function (ids) {
                const videodetails = hookResult.videodetails.data.detailInfo;
                let mediaUrl = "";
                let episodeKey = "";
                hookResult.playdata.data.list.forEach((item) => {
                    if (mediaUrl === "" && item.mediaUrl !== "") {
                        mediaUrl = item.mediaUrl;
                        episodeKey = item.episodeKey;
                    }
                })
                let media = [];
                if (videodetails.videoType !== 0) {
                    if (typeof hookResult.videochoosegather !== "undefined") {
                        hookResult.videochoosegather.data.list.forEach((item) => {
                            if (videodetails.episodeTitle === item.episodeTitle) {
                                media.push({
                                    name: item.episodeTitle,
                                    type: "finalUrl",
                                    ext: {
                                        "header": {
                                            "User-Agent": window.navigator.userAgent,
                                            "Referer": window.location.href
                                        },
                                        "url": mediaUrl
                                    }
                                });
                            } else {
                                media.push({
                                    name: item.episodeTitle,
                                    type: "webview",
                                    ext: {
                                        replace: {
                                            mediaKey: item.mediaKey,
                                            episodeKey: item.episodeKey
                                        }
                                    }
                                })
                            }
                        })
                    } else {
                        spiderExecuted = false;
                        return;
                    }
                } else {
                    media.push({
                        name: videodetails.episodeTitle,
                        type: "finalUrl",
                        ext: {
                            "header": {
                                "User-Agent": window.navigator.userAgent,
                                "Referer": window.location.href
                            },
                            "url": mediaUrl
                        }
                    })
                }
                return {
                    vod_id: videodetails.mediaKey,
                    vod_name: videodetails.title,
                    vod_pic: videodetails.coverImgUrl,
                    vod_actor: videodetails.actor,
                    vod_director: videodetails.director,
                    vod_tag: videodetails.cidMapper,
                    vod_area: videodetails.regional,
                    vod_content: videodetails.introduce,
                    vod_play_data: [{
                        from: "书生玩剣ⁱ·*₁＇",
                        media: media
                    }]
                };
            },
            playerContent: function (flag, id, vipFlags) {
                let mediaUrl = "";
                hookResult.playdata.data.list.forEach((item) => {
                    if (mediaUrl === "" && item.mediaUrl !== "") {
                        mediaUrl = item.mediaUrl;
                    }
                })
                return {
                    type: "finalUrl",
                    ext: {
                        "header": {
                            "User-Agent": window.navigator.userAgent,
                            "Referer": window.location.href
                        },
                        "url": mediaUrl
                    }
                };
            },
            searchContent: function (key, quick, pg) {
                console.log(hookResult);
                let result = {
                    list: [],
                    pagecount: 1
                };
                if (pg == 1) {
                    hookResult.titlegetdata.data.list.forEach((media) => {
                        result.list.push({
                            vod_id: media.mediaKey,
                            vod_name: media.title,
                            vod_pic: media.coverImgUrl,
                            vod_remarks: media.updateStatus,
                            vod_year: media.regional
                        })
                    })
                }
                return result;
            }
        };
    })();
    let spiderExecuted = false;
    let dataReadyCount = 0;
    let hookResult = {};
    const {unProxy, originXhr} = proxy({
        onRequest: (config, handler) => {
            hookConfigs[GMSpiderArgs.fName].forEach((hookConfig) => {
                if (typeof hookConfig.onRequestHook === "function" && hookConfig.matcher.match(config.url)) {
                    hookConfig.onRequestHook(config, handler);
                }
            });
            handler.next(config);
        },
        onResponse: (response, handler) => {
            if (!spiderExecuted) {
                let dataTodoCount = 0;
                hookConfigs[GMSpiderArgs.fName].forEach((hookConfig) => {
                    if (typeof hookConfig.dataKey !== "undefined") {
                        if (hookConfig?.require !== false) {
                            dataTodoCount++;
                        }
                        if (hookConfig.matcher.match(response.config.url)) {
                            if (hookConfig?.require !== false) {
                                dataReadyCount++;
                            }
                            try {
                                let data = JSON.parse(response.response);
                                if (typeof data === 'object' && data) {
                                    hookResult[hookConfig.dataKey] = data;
                                } else {
                                    hookResult[hookConfig.dataKey] = response.response;
                                }
                            } catch (e) {
                            }
                        }
                    }
                    if (typeof hookConfig.onResponseHook === "function" && hookConfig.matcher.match(response.config.url)) {
                        hookConfig.onResponseHook(response, handler);
                    }
                });
                if (dataTodoCount === dataReadyCount) {
                    spiderExecuted = true;
                    const result = GmSpider[GMSpiderArgs.fName](...GMSpiderArgs.fArgs);
                    console.log(result);
                    if (typeof GmSpiderInject !== 'undefined' && spiderExecuted) {
                        GmSpiderInject.SetSpiderResult(JSON.stringify(result));
                    }
                }
            }
            handler.next(response);
        }
    }, unsafeWindow)
})();
