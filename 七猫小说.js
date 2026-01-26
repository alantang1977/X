/**
 * 七猫中文网(qimao.com)爬虫
 * 作者：助手
 * 版本：1.0
 * 最后更新：2026-01-26
 * 发布页 https://www.qimao.com/
 */

function qimaoSpider() {
    const baseUrl = 'https://www.qimao.com';
    
    /**
     * 提取视频列表数据（私有方法）
     * @param {Document} document - DOM文档对象
     * @param {string} selector - 选择器，可选
     * @returns {Array} 书籍数据数组
     */
    const extractBooks = (document, selector = '.book-list-item, .rank-list-box-list-item, .qm-ranking-list-item') => {
        const books = [];
        
        // 方法1：从.book-list-item提取（签约新书、改编与出版等）
        const bookItems = document.querySelectorAll('.book-list-item');
        bookItems.forEach(item => {
            const titleEl = item.querySelector('.s-title, .s-title-two, [class*="title"] a');
            const authorEl = item.querySelector('.s-author a');
            const imgEl = item.querySelector('img.book-cover-src');
            const linkEl = item.querySelector('a[href*="/shuku/"]');
            
            let bookId = linkEl?.getAttribute('href') || '';
            if (bookId && !bookId.startsWith('http')) {
                bookId = baseUrl + (bookId.startsWith('/') ? '' : '/') + bookId;
            }
            
            let bookPic = imgEl?.src || '';
            if (bookPic && !bookPic.startsWith('http')) {
                bookPic = baseUrl + (bookPic.startsWith('/') ? '' : '/') + bookPic;
            }
            
            const book = {
                vod_name: titleEl?.textContent?.trim() || '',
                vod_pic: bookPic,
                vod_remarks: '', // 可以在后续补充
                vod_id: bookId,
                vod_actor: authorEl?.textContent?.trim() || '',
                vod_score: item.querySelector('.s-score .num')?.textContent || '',
                vod_content: item.querySelector('.s-recommend, .s-intro')?.textContent?.trim() || ''
            };
            
            if (book.vod_name) {
                books.push(book);
            }
        });
        
        // 方法2：从.rank-list-box-list-item提取（排行榜）
        const rankItems = document.querySelectorAll('.rank-list-box-list-item');
        rankItems.forEach(item => {
            const titleEl = item.querySelector('.s-tit a');
            const authorEl = item.querySelector('.s-des a');
            const imgEl = item.querySelector('img.book-cover-src');
            const heatEl = item.querySelector('.s-heat em');
            
            const link = titleEl?.getAttribute('href');
            let bookId = '';
            if (link) {
                bookId = link.startsWith('http') ? link : baseUrl + link;
            }
            
            let bookPic = imgEl?.src || '';
            if (bookPic && !bookPic.startsWith('http')) {
                bookPic = baseUrl + (bookPic.startsWith('/') ? '' : '/') + bookPic;
            }
            
            const book = {
                vod_name: titleEl?.textContent?.trim() || '',
                vod_pic: bookPic,
                vod_remarks: heatEl ? `${heatEl.textContent}万热度` : '',
                vod_id: bookId,
                vod_actor: authorEl?.textContent?.trim() || ''
            };
            
            if (book.vod_name) {
                books.push(book);
            }
        });
        
        // 方法3：从.qm-ranking-list-item提取（分类推荐）
        const rankingItems = document.querySelectorAll('.qm-ranking-list-item');
        rankingItems.forEach(item => {
            const titleEl = item.querySelector('.book-title a');
            const authorEl = item.querySelector('.s-author a');
            const imgEl = item.querySelector('img.book-cover-src');
            
            const link = titleEl?.getAttribute('href');
            let bookId = '';
            if (link) {
                bookId = link.startsWith('http') ? link : baseUrl + link;
            }
            
            let bookPic = imgEl?.src || '';
            if (bookPic && !bookPic.startsWith('http')) {
                bookPic = baseUrl + (bookPic.startsWith('/') ? '' : '/') + bookPic;
            }
            
            const book = {
                vod_name: titleEl?.textContent?.trim() || '',
                vod_pic: bookPic,
                vod_remarks: item.querySelector('.s-score .num')?.textContent ? `${item.querySelector('.s-score .num').textContent}万人气` : '',
                vod_id: bookId,
                vod_actor: authorEl?.textContent?.trim() || '',
                vod_content: item.querySelector('.s-intro')?.textContent?.trim() || ''
            };
            
            if (book.vod_name) {
                books.push(book);
            }
        });
        
        return books.filter(book => book.vod_name && book.vod_id);
    };
    
    /**
     * 提取最近更新数据
     */
    const extractLatestUpdates = (document) => {
        const updates = [];
        const rows = document.querySelectorAll('.qm-table-body li');
        
        rows.forEach(row => {
            const categoryEl = row.querySelector('.category_name a');
            const titleEl = row.querySelector('.td:nth-child(2) a');
            const chapterEl = row.querySelector('.td:nth-child(3) a');
            const authorEl = row.querySelector('.td:nth-child(4) a');
            const timeEl = row.querySelector('.td:nth-child(5)');
            
            if (titleEl && chapterEl) {
                const bookLink = titleEl.getAttribute('href');
                const chapterLink = chapterEl.getAttribute('href');
                
                updates.push({
                    category_name: categoryEl?.textContent?.trim() || '',
                    vod_name: titleEl.textContent.trim(),
                    latest_chapter: chapterEl.textContent.trim(),
                    vod_actor: authorEl?.textContent?.trim() || '',
                    update_time: timeEl?.textContent?.trim() || '',
                    vod_id: bookLink ? (bookLink.startsWith('http') ? bookLink : baseUrl + bookLink) : '',
                    chapter_url: chapterLink ? (chapterLink.startsWith('http') ? chapterLink : baseUrl + chapterLink) : ''
                });
            }
        });
        
        return updates;
    };

    return {
        async init(cfg) {
            return {
                webview: {
                    debug: true,
                    showWebView: false,
                    widthPercent: 80,
                    heightPercent: 60,
                    keyword: '',
                    returnType: 'dom',
                    timeout: 30,
                    blockImages: true,
                    enableJavaScript: true,
                    header: {
                        'Referer': baseUrl,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                }
            };
        },
        
        async homeContent(filter) {
            console.log("homeContent 开始执行, filter:", filter);

            return {
                class: [
                    { type_id: "1", type_name: "女生原创" },
                    { type_id: "0", type_name: "男生原创" },
                    { type_id: "2", type_name: "古代情缘" },
                    { type_id: "8", type_name: "总裁豪门" },
                    { type_id: "58", type_name: "架空历史" },
                    { type_id: "37", type_name: "东方玄幻" },
                    { type_id: "209", type_name: "宫闱宅斗" },
                    { type_id: "278", type_name: "年代重生" }
                ]
            };
        },
        
        async homeVideoContent() {
            console.log("homeVideoContent 开始执行");

            const document = await Java.wvOpen(baseUrl + '/');
            const books = [];
            
            // 1. 提取排行榜数据（大热榜、新书榜）
            const rankSections = document.querySelectorAll('.rank-list-box');
            rankSections.forEach(section => {
                const sectionBooks = extractBooks(section);
                books.push(...sectionBooks);
            });
            
            // 2. 提取改编与出版
            const publishSection = document.querySelector('.qm-mod:has(em:contains("改编与出版"))');
            if (publishSection) {
                const publishBooks = extractBooks(publishSection);
                books.push(...publishBooks);
            }
            
            // 3. 提取签约新书
            const newBookSection = document.querySelector('.qm-mod:has(em:contains("签约新书"))');
            if (newBookSection) {
                const newBooks = extractBooks(newBookSection);
                books.push(...newBooks);
            }
            
            // 4. 提取征文作品（女频创新大征文、男频大征文）
            const topicSections = document.querySelectorAll('.qm-mod:has(.topic-tag)');
            topicSections.forEach(section => {
                const topicBooks = extractBooks(section);
                books.push(...topicBooks);
            });
            
            // 5. 提取总编推荐
            const editorSection = document.querySelector('.qm-mod:has(em:contains("总编推荐"))');
            if (editorSection) {
                const editorBooks = extractBooks(editorSection);
                books.push(...editorBooks);
            }
            
            console.log("首页取到的书籍列表", books.length);
            return { list: books.slice(0, 50) }; // 限制返回数量
        },
        
        async categoryContent(tid, pg, filter, extend) {
            console.log("categoryContent - tid:", tid, "pg:", pg);
            
            // 构建分类页URL
            // 注意：这里的URL模式需要根据实际网站结构调整
            let url = `${baseUrl}/shuku/`;
            
            // 根据tid构建不同的URL
            if (tid === "1") {
                // 女生原创
                url = `${baseUrl}/shuku/1-a-a-a-a-a-a-click-1/`;
            } else if (tid === "0") {
                // 男生原创
                url = `${baseUrl}/shuku/0-a-a-a-a-a-a-click-1/`;
            } else if (tid === "2") {
                // 古代情缘
                url = `${baseUrl}/shuku/a-2-216-a-a-a-a-click-1/`;
            } else if (tid === "8") {
                // 总裁豪门
                url = `${baseUrl}/shuku/a-1-8-a-a-a-a-click-1/`;
            } else if (tid === "58") {
                // 架空历史
                url = `${baseUrl}/shuku/a-56-58-a-a-a-a-click-1/`;
            } else if (tid === "37") {
                // 东方玄幻
                url = `${baseUrl}/shuku/a-202-37-a-a-a-a-click-1/`;
            } else if (tid === "209") {
                // 宫闱宅斗
                url = `${baseUrl}/shuku/a-2-209-a-a-a-a-click-1/`;
            } else if (tid === "278") {
                // 年代重生
                url = `${baseUrl}/shuku/a-1-278-a-a-a-a-click-1/`;
            }
            
            // 处理分页
            if (pg > 1) {
                // 七猫的分页规则通常是加页码后缀
                url = url.replace(/-click-1\//, `-click-${pg}/`);
            }
            
            console.log("分类页URL:", url);
            const document = await Java.wvOpen(url);
            const books = extractBooks(document);
            
            // 提取分页信息
            let currentPage = pg || 1;
            let totalPages = 1;
            
            const pageEl = document.querySelector('.hl-page-total');
            if (pageEl) {
                const pageText = pageEl.textContent;
                const match = pageText.match(/(\d+)\s*\/\s*(\d+)/);
                if (match) {
                    currentPage = parseInt(match[1]) || currentPage;
                    totalPages = parseInt(match[2]) || 1;
                }
            }

            console.log("categoryContent 返回数据，数量:", books.length);
            
            return {
                code: 1,
                msg: "数据列表",
                list: books,
                page: currentPage,
                pagecount: totalPages,
                limit: 20,
                total: totalPages * 20
            };
        },
        
        async detailContent(ids) {
            console.log("detailContent - ids:", ids[0]);
            const document = await Java.wvOpen(ids[0]);

            // 提取基本信息
            const title = document.querySelector('.book-title, h1')?.textContent?.trim() || '';
            
            // 提取封面图片
            const imgEl = document.querySelector('.book-cover-src, .qm-book-cover img');
            let vodPic = imgEl?.src || '';
            
            // 处理图片地址
            if (vodPic && !vodPic.startsWith('http')) {
                vodPic = baseUrl + (vodPic.startsWith('/') ? '' : '/') + vodPic;
            }
            
            // 提取作者
            let vod_actor = '';
            const authorEl = document.querySelector('.author-name a, .s-author a');
            if (authorEl) {
                vod_actor = authorEl.textContent.trim();
            }
            
            // 提取作品信息
            let vod_year = '', vod_area = '', vod_remarks = '', type_name = '';
            const infoElements = document.querySelectorAll('.book-info, .book-intr');
            
            infoElements.forEach(el => {
                const text = el.textContent;
                if (text.includes('完结') || text.includes('连载中')) {
                    vod_remarks = text.split('·')[0]?.trim() || '';
                }
                if (text.includes('万字')) {
                    // 可以提取字数信息
                }
            });
            
            // 提取分类信息
            const categoryEl = document.querySelector('.s-category a, .book-info a');
            if (categoryEl) {
                type_name = categoryEl.textContent.trim();
            }
            
            // 提取简介
            const vod_content = document.querySelector('.book-intro, .s-recommend, .s-intro')?.textContent?.trim() || 
                              document.querySelector('.detail-content')?.textContent?.trim() || '';
            
            // 提取目录/章节列表
            const playlists = [];
            const chapterList = document.querySelector('.chapter-list, .catalog-list');
            
            if (chapterList) {
                const episodes = [];
                const chapters = chapterList.querySelectorAll('a');
                
                chapters.forEach((link, index) => {
                    const title = link.textContent?.trim() || `第${index + 1}章`;
                    const href = link.getAttribute('href');
                    
                    if (href) {
                        const chapterUrl = href.startsWith('http') ? href : baseUrl + href;
                        episodes.push(`${title}$${chapterUrl}`);
                    }
                });
                
                if (episodes.length > 0) {
                    playlists.push({
                        title: '目录',
                        episodes: episodes.slice(0, 50) // 限制前50章
                    });
                }
            }
            
            // 构建书籍详情
            const book = {
                code: 1,
                msg: "数据列表",
                page: 1,
                pagecount: 1,
                limit: 1,
                total: 1,
                list: [{
                    vod_id: ids[0],
                    vod_name: title,
                    vod_pic: vodPic,
                    vod_remarks: vod_remarks,
                    vod_year: vod_year,
                    vod_actor: vod_actor,
                    vod_director: '',
                    vod_area: vod_area || '中国',
                    vod_lang: '中文',
                    vod_content: vod_content,
                    vod_play_from: playlists.length > 0 ? playlists.map(p => p.title).join('$$$') : '目录',
                    vod_play_url: playlists.length > 0 ? playlists.map(p => p.episodes.join('#')).join('$$$') : '',
                    type_name: type_name
                }]
            };
            
            console.log("detailContent 返回数据");
            return book;
        },
        
        async searchContent(key, quick, pg) {
            console.log("searchContent - key:", key, "quick:", quick, "pg:", pg);
            
            // 构建搜索URL
            const searchUrl = `${baseUrl}/search/?keyword=${encodeURIComponent(key)}`;
            
            try {
                const document = await Java.wvOpen(searchUrl);
                const books = extractBooks(document);
                
                // 如果没有找到书籍，尝试其他选择器
                if (books.length === 0) {
                    const searchItems = document.querySelectorAll('.search-result-item, .book-item');
                    searchItems.forEach(item => {
                        const titleEl = item.querySelector('.title a, .book-title a');
                        const authorEl = item.querySelector('.author, .book-author');
                        const imgEl = item.querySelector('img');
                        
                        if (titleEl) {
                            const link = titleEl.getAttribute('href');
                            books.push({
                                vod_name: titleEl.textContent.trim(),
                                vod_pic: imgEl?.src || '',
                                vod_remarks: '',
                                vod_id: link ? (link.startsWith('http') ? link : baseUrl + link) : '',
                                vod_actor: authorEl?.textContent?.trim() || ''
                            });
                        }
                    });
                }
                
                return {
                    list: books,
                    page: 1,
                    pagecount: 1,
                    limit: 20,
                    total: books.length
                };
            } catch (error) {
                console.log("搜索失败:", error);
                return { list: [] };
            }
        },
        
        async playerContent(flag, id, vipFlags) {
            console.log("playerContent - flag:", flag, "id:", id, "vipFlags:", vipFlags);
            
            // 对于小说网站，playerContent通常是阅读页面
            // id可能是章节URL
            if (id && id.includes('shuku/')) {
                return {
                    url: id,
                    parse: 1,
                    header: {
                        'Referer': baseUrl,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                };
            }
            
            // 默认返回首页
            return {
                url: baseUrl,
                parse: 1,
                header: {
                    'Referer': baseUrl,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            };
        },
        
        async action(actionStr) {
            console.log("action - actionStr:", actionStr);
            try {
                const params = JSON.parse(actionStr);
                console.log("action params:", params);
                
                if (params.action === 'getLatestUpdates') {
                    // 获取最近更新
                    const document = await Java.wvOpen(baseUrl + '/');
                    const updates = extractLatestUpdates(document);
                    
                    return {
                        updates: updates,
                        count: updates.length,
                        timestamp: new Date().toISOString()
                    };
                }
                
                if (params.action === 'getRanking') {
                    // 获取排行榜
                    const type = params.type || 'hot'; // hot, new, over
                    const gender = params.gender || 'girl'; // girl, boy
                    
                    const rankUrl = `${baseUrl}/paihang/${gender}/${type}/date/`;
                    const document = await Java.wvOpen(rankUrl);
                    const books = extractBooks(document);
                    
                    return {
                        type: type,
                        gender: gender,
                        books: books,
                        count: books.length
                    };
                }
                
            } catch (e) {
                console.log("action is not JSON, treat as string");
            }
            return { list: [] };
        }
    };
}

const spider = qimaoSpider();
spider;
