<?php
// 引入文件解析器
require_once 'parser.php';

// 处理阅读格式 - 新增代码
if (isset($_GET['format'])) {
    setcookie('preferredReadingFormat', $_GET['format'], time() + 31536000, '/');
    $format = $_GET['format'];
} elseif (isset($_COOKIE['preferredReadingFormat'])) {
    $format = $_COOKIE['preferredReadingFormat'];
} else {
    $format = 'default';
}

// 获取请求参数
$index = isset($_GET['index']) ? (int)$_GET['index'] : 0;
$file = isset($_GET['file']) ? $_GET['file'] : null;

// 初始化内容
$novelTitle = '';
$chapterTitle = '';
$chapterContent = '';
$fileType = 'text';
$imageData = '';
$fileInfo = [];
$isPdf = false;
$pdfFilePath = '';

// 检查文件是否存在
if ($file) {
    // 使用 parser.php 获取文件内容
    $contentResult = get_file_content($file, $index);
    
    if ($contentResult['success']) {
        $fileType = $contentResult['type'];
        $fileInfo = pathinfo($file);
        $novelTitle = $fileInfo['filename'];
        
        if ($fileType === 'text') {
            $chapterTitle = $contentResult['chapter_title'];
            $chapterContent = $contentResult['chapter_content'];
        } elseif ($fileType === 'image') {
            $imageData = $contentResult['image_data'];
            $chapterTitle = '图片预览 - ' . $contentResult['file_name'];
            $imageWidth = $contentResult['width'];
            $imageHeight = $contentResult['height'];
        } elseif ($fileType === 'pdf') {
            $isPdf = true;
            $chapterTitle = 'PDF文档 - ' . $contentResult['file_name'];
            
            // 使用相对路径
            $pdfFilePath = isset($contentResult['file_url']) ? $contentResult['file_url'] : './xs/' . rawurlencode($file);
            
            // 确保路径正确
            if (empty($pdfFilePath)) {
                $pdfFilePath = './xs/' . rawurlencode($file);
            }
        } elseif ($fileType === 'ebook') {
            $chapterTitle = '电子书 - ' . $contentResult['file_name'];
            $chapterContent = $contentResult['message'];
            $fileExtension = $contentResult['extension'];
        }
    }
}
?>

<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title><?php 
        if ($fileType === 'text') {
            echo $novelTitle ? htmlspecialchars($novelTitle) . ' - ' . htmlspecialchars($chapterTitle) : '章节内容';
        } elseif ($fileType === 'image') {
            echo htmlspecialchars($chapterTitle);
        } elseif ($fileType === 'pdf') {
            echo htmlspecialchars($chapterTitle);
        } else {
            echo htmlspecialchars($chapterTitle);
        }
    ?></title>
    
    <!-- 引入PDF.js -->
    <?php if ($isPdf): ?>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script>pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';</script>
    <?php endif; ?>
    
    <style>
        :root {
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --accent-color: #e74c3c;
            --bg-color: #f8f5f0;
            --text-color: #2c3e50;
            --card-bg: #ffffff;
            --border-color: #e0d6c8;
            --shadow: 0 4px 12px rgba(0,0,0,0.08);
            
            /* 阅读格式相关变量 */
            --font-family-base: "Microsoft YaHei", "微软雅黑", "PingFang SC", "Helvetica Neue", Arial, sans-serif;
            --font-family-serif: "Noto Serif SC", "Source Han Serif SC", "SimSun", serif;
            --font-family-classic: "STKaiti", "KaiTi", "楷体", serif;
            --line-height-base: 1.6;
            --paragraph-spacing: 1.2em;
            --text-indent: 2em;
            
            /* 安全区域支持 */
            --safe-area-inset-left: env(safe-area-inset-left);
            --safe-area-inset-right: env(safe-area-inset-right);
            --safe-area-inset-top: env(safe-area-inset-top);
            --safe-area-inset-bottom: env(safe-area-inset-bottom);
        }
        
        .dark-mode {
            --primary-color: #ecf0f1;
            --secondary-color: #3498db;
            --accent-color: #e74c3c;
            --bg-color: #1a1a1a;
            --text-color: #ecf0f1;
            --card-bg: #2d2d2d;
            --border-color: #444;
            --shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        /* 系统级深色模式适配 */
        @media (prefers-color-scheme: dark) {
            :root:not(.dark-mode) {
                --primary-color: #ecf0f1;
                --secondary-color: #3498db;
                --accent-color: #e74c3c;
                --bg-color: #1a1a1a;
                --text-color: #ecf0f1;
                --card-bg: #2d2d2d;
                --border-color: #444;
                --shadow: 0 4px 12px rgba(0,0,0,0.3);
            }
        }
        
        /* 运动偏好减少 */
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
        
        /* 高对比度模式优化 */
        @media (prefers-contrast: high) {
            :root {
                --border-color: #000;
                --shadow: 0 2px 8px rgba(0,0,0,0.8);
            }
        }
        
        /* PDF阅读器样式 */
        .pdf-container {
            width: 100%;
            background: var(--card-bg);
            border-radius: 10px;
            padding: 20px;
            box-shadow: var(--shadow);
            margin-bottom: 20px;
        }
        
        .pdf-controls {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(0,0,0,0.05);
            border-radius: 8px;
            flex-wrap: wrap;
        }
        
        .dark-mode .pdf-controls {
            background: rgba(255,255,255,0.05);
        }
        
        .pdf-btn {
            padding: 8px 16px;
            border: 1px solid var(--border-color);
            background: var(--card-bg);
            color: var(--text-color);
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .pdf-btn:hover {
            background: var(--secondary-color);
            color: white;
            transform: translateY(-1px);
        }
        
        .pdf-page-info {
            font-size: 0.9em;
            color: var(--text-color);
            min-width: 100px;
            text-align: center;
        }
        
        .pdf-page-input {
            width: 60px;
            padding: 5px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background: var(--card-bg);
            color: var(--text-color);
            text-align: center;
        }
        
        .pdf-viewer {
            width: 100%;
            min-height: 500px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: auto;
            background: #f9f9f9;
        }
        
        .dark-mode .pdf-viewer {
            background: #2a2a2a;
        }
        
        .pdf-canvas {
            display: block;
            margin: 0 auto;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            max-width: 100%;
        }
        
        .pdf-loading {
            text-align: center;
            padding: 40px;
            color: var(--text-color);
            font-size: 1.1em;
        }
        
        .pdf-error {
            text-align: center;
            padding: 40px;
            color: var(--accent-color);
            background: rgba(231, 76, 60, 0.1);
            border-radius: 8px;
            margin: 20px 0;
        }
        
        .pdf-zoom-controls {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .zoom-btn {
            width: 36px;
            height: 36px;
            border: 1px solid var(--border-color);
            background: var(--card-bg);
            color: var(--text-color);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.2s;
        }
        
        .zoom-btn:hover {
            background: var(--secondary-color);
            color: white;
        }
        
        .zoom-display {
            font-size: 0.9em;
            color: var(--text-color);
            min-width: 50px;
            text-align: center;
        }
        
        /* 阅读格式样式 */
        .format-default {
            --reading-font-family: var(--font-family-base);
            --reading-line-height: 1.8;
            --reading-font-size: 1.05em;
            --reading-paragraph-spacing: 1.5em;
            --reading-text-indent: 2em;
            --reading-max-width: 680px;
        }

        .format-page {
            --reading-font-family: var(--font-family-base);
            --reading-line-height: 1.6;
            --reading-font-size: 1.1em;
            --reading-paragraph-spacing: 1.5em;
            --reading-text-indent: 2em;
            --reading-max-width: 100%;
            min-height: 100vh;
        }

        .format-comic {
            --reading-font-family: "Comic Sans MS", "楷体", cursive;
            --reading-line-height: 1.4;
            --reading-font-size: 1.2em;
            --reading-paragraph-spacing: 1em;
            --reading-text-indent: 0;
            --reading-max-width: 100%;
        }

        .format-classic {
            --reading-font-family: var(--font-family-classic);
            --reading-line-height: 2.0;
            --reading-font-size: 1.15em;
            --reading-paragraph-spacing: 2em;
            --reading-text-indent: 2em;
            --reading-max-width: 800px;
        }

        .format-modern {
            --reading-font-family: "Helvetica Neue", Arial, sans-serif;
            --reading-line-height: 1.7;
            --reading-font-size: 1.05em;
            --reading-paragraph-spacing: 1.5em;
            --reading-text-indent: 0;
            --reading-max-width: 650px;
        }
        
        /* 新增阅读格式样式 */
        .format-professional {
            --reading-font-family: "Georgia", "Times New Roman", "Noto Serif SC", serif;
            --reading-line-height: 1.8;
            --reading-font-size: 1.1em;
            --reading-paragraph-spacing: 1.8em;
            --reading-text-indent: 0;
            --reading-max-width: 750px;
        }

        .format-eye-care {
            --reading-font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", sans-serif;
            --reading-line-height: 1.9;
            --reading-font-size: 1.05em;
            --reading-paragraph-spacing: 1.6em;
            --reading-text-indent: 2.5em;
            --reading-max-width: 700px;
        }

        .format-dark-eye-care {
            --reading-font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", sans-serif;
            --reading-line-height: 1.9;
            --reading-font-size: 1.05em;
            --reading-paragraph-spacing: 1.6em;
            --reading-text-indent: 2.5em;
            --reading-max-width: 700px;
        }

        .format-magazine {
            --reading-font-family: "Helvetica Neue", "Arial", "PingFang SC", sans-serif;
            --reading-line-height: 1.5;
            --reading-font-size: 0.95em;
            --reading-paragraph-spacing: 1.2em;
            --reading-text-indent: 0;
            --reading-max-width: 100%;
        }
        
        /* 应用阅读格式 */
        body[data-format] {
            font-family: var(--reading-font-family);
            line-height: var(--reading-line-height);
        }
        
        body[data-format] .chapter-content {
            font-size: var(--reading-font-size);
            max-width: var(--reading-max-width);
            margin: 0 auto;
        }
        
        body[data-format] .chapter-content p {
            margin-bottom: var(--reading-paragraph-spacing);
            text-indent: var(--reading-text-indent);
        }

        /* 分页模式特定样式 */
        .format-page .chapter-content {
            column-width: 300px;
            column-gap: 40px;
            column-rule: 1px solid var(--border-color);
        }
        
        @media screen and (max-width: 768px) {
            .format-page .chapter-content {
                column-count: 1;
            }
        }
        
        /* 漫画模式特定样式 */
        .format-comic .chapter-content p {
            background: var(--card-bg);
            padding: 15px;
            margin: 10px 0;
            border-radius: 15px;
            border: 3px solid var(--border-color);
            box-shadow: 5px 5px 0 rgba(0, 0, 0, 0.1);
        }
        
        /* 现代模式段落样式 */
        .format-modern .chapter-content p {
            border-left: 3px solid var(--secondary-color);
            padding-left: 15px;
            margin-left: 0;
        }

        /* 专业模式特定样式 */
        .format-professional .chapter-content {
            background: linear-gradient(90deg, #f8f9fa 0%, #ffffff 5%, #ffffff 95%, #f8f9fa 100%);
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border-left: 4px solid #3498db;
        }

        .format-professional .chapter-content p:first-child::first-letter {
            font-size: 3em;
            float: left;
            line-height: 1;
            margin-right: 8px;
            color: #3498db;
            font-weight: bold;
        }

        /* 护眼模式特定样式 */
        .format-eye-care .chapter-content {
            background-color: #e8f5e8;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(139, 195, 74, 0.2);
            color: #2d5016;
            border: 1px solid #c8e6c9;
        }

        .format-eye-care .chapter-content p {
            background: rgba(255, 255, 255, 0.7);
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(139, 195, 74, 0.1);
        }

        /* 黑暗护眼模式特定样式 */
        .format-dark-eye-care .chapter-content {
            background: linear-gradient(135deg, #1a2f1a 0%, #2d4d2d 100%);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(76, 175, 80, 0.2);
            color: #e8f5e8;
            border: 1px solid #4caf50;
        }

        .format-dark-eye-care .chapter-content p {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(76, 175, 80, 0.2);
            backdrop-filter: blur(10px);
        }

        /* 杂志模式特定样式 */
        .format-magazine .chapter-content {
            column-count: 2;
            column-gap: 40px;
            column-rule: 2px solid var(--border-color);
            padding: 20px;
        }

        .format-magazine .chapter-content p:first-child {
            font-weight: bold;
            font-size: 1.1em;
            column-span: all;
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid var(--secondary-color);
            padding-bottom: 15px;
        }

        .format-magazine .chapter-content p:first-child::after {
            content: "❧";
            display: block;
            font-size: 2em;
            color: var(--secondary-color);
            margin-top: 10px;
        }

        @media screen and (max-width: 768px) {
            .format-magazine .chapter-content {
                column-count: 1;
            }
        }
        
        /* 基础样式 */
        * {
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
            transition: background-color 0.3s, color 0.3s;
        }
        
        body {
            font-family: var(--font-family-base);
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 0;
            line-height: var(--line-height-base);
            -webkit-text-size-adjust: 100%;
            min-height: 100vh;
            /* 安全区域支持 */
            padding-left: var(--safe-area-inset-left);
            padding-right: var(--safe-area-inset-right);
            padding-top: var(--safe-area-inset-top);
            padding-bottom: var(--safe-area-inset-bottom);
        }
        
        /* 字体大小控制类 */
        body.font-small {
            --reading-font-size: 0.85em;
        }
        
        body.font-medium {
            --reading-font-size: 1em;
        }
        
        body.font-large {
            --reading-font-size: 1.15em;
        }
        
        body.font-xlarge {
            --reading-font-size: 1.3em;
        }
        
        .header {
            background-color: var(--card-bg);
            padding: 15px 20px;
            box-shadow: var(--shadow);
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            justify-content: space-between;
            align-items: center;
            /* 安全区域支持 */
            padding-left: calc(20px + var(--safe-area-inset-left));
            padding-right: calc(20px + var(--safe-area-inset-right));
            padding-top: calc(15px + var(--safe-area-inset-top));
        }
        
        .header h1 {
            margin: 0;
            font-size: 1.4em;
            font-weight: 600;
            color: var(--primary-color);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 50%;
        }
        
        .controls {
            display: flex;
            gap: 8px;
        }
        
        .control-btn {
            background: none;
            border: 1px solid var(--border-color);
            color: var(--text-color);
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 1.1em;
            transition: all 0.2s ease;
            -webkit-tap-highlight-color: transparent;
        }
        
        /* 触摸设备优化 */
        @media (hover: none) and (pointer: coarse) {
            .control-btn:hover, .scroll-btn:hover, .tts-btn:hover, .pdf-btn:hover, .zoom-btn:hover {
                transform: none;
                background-color: transparent;
            }
            
            .control-btn:active, .scroll-btn:active, .tts-btn:active, .pdf-btn:active, .zoom-btn:active {
                background-color: rgba(0,0,0,0.05);
                transform: scale(0.95);
            }
            
            .dark-mode .control-btn:active, 
            .dark-mode .scroll-btn:active,
            .dark-mode .tts-btn:active,
            .dark-mode .pdf-btn:active,
            .dark-mode .zoom-btn:active {
                background-color: rgba(255,255,255,0.05);
            }
        }
        
        /* 非触摸设备悬停效果 */
        @media (hover: hover) {
            .control-btn:hover, .scroll-btn:hover, .tts-btn:hover, .pdf-btn:hover, .zoom-btn:hover {
                background-color: rgba(0,0,0,0.05);
                transform: scale(1.05);
            }
            
            .dark-mode .control-btn:hover, 
            .dark-mode .scroll-btn:hover,
            .dark-mode .tts-btn:hover,
            .dark-mode .pdf-btn:hover,
            .dark-mode .zoom-btn:hover {
                background-color: rgba(255,255,255,0.1);
            }
        }
        
        .control-btn.active {
            background-color: var(--secondary-color);
            color: white;
            border-color: var(--secondary-color);
        }
        
        .container {
            width: 100%;
            max-width: 100%;
            margin: 0 auto;
            background-color: var(--card-bg);
            padding: 20px;
            min-height: 100vh;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            /* 安全区域支持 */
            padding-left: calc(20px + var(--safe-area-inset-left));
            padding-right: calc(20px + var(--safe-area-inset-right));
            padding-bottom: calc(20px + var(--safe-area-inset-bottom));
        }
        
        .chapter-content {
            line-height: var(--reading-line-height, 1.8);
            text-align: justify;
            word-wrap: break-word;
            overflow-wrap: break-word;
            padding: 0 10px;
            font-size: var(--reading-font-size, 1em);
        }
        
        .chapter-content p {
            margin-bottom: var(--reading-paragraph-spacing, 1.2em);
            text-indent: var(--reading-text-indent, 2em);
        }
        
        .loading {
            text-align: center;
            font-size: 1.2rem;
            padding: 20px;
            color: var(--text-color);
        }
        
        /* 章节分隔线 */
        .chapter-divider {
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--secondary-color), transparent);
            margin: 30px 0;
            border: none;
        }
        
        /* 字体大小指示器 */
        .font-indicator {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 8px 15px;
            font-size: 0.9em;
            box-shadow: var(--shadow);
            opacity: 0;
            transition: opacity 0.3s;
            z-index: 1000;
            /* 安全区域支持 */
            right: calc(20px + var(--safe-area-inset-right));
            bottom: calc(20px + var(--safe-area-inset-bottom));
        }
        
        .font-indicator.show {
            opacity: 1;
        }
        
        /* 阅读格式指示器 */
        .format-indicator {
            position: fixed;
            bottom: 70px;
            right: 20px;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 8px 15px;
            font-size: 0.9em;
            box-shadow: var(--shadow);
            opacity: 0;
            transition: opacity 0.3s;
            z-index: 1000;
            /* 安全区域支持 */
            right: calc(20px + var(--safe-area-inset-right));
            bottom: calc(70px + var(--safe-area-inset-bottom));
        }
        
        .format-indicator.show {
            opacity: 1;
        }
        
        /* 自动滚动指示器 */
        .auto-scroll-indicator {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--accent-color);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            box-shadow: var(--shadow);
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .auto-scroll-indicator.show {
            opacity: 1;
        }
        
        /* TTS状态指示器 */
        .tts-indicator {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--secondary-color);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            box-shadow: var(--shadow);
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .tts-indicator.show {
            opacity: 1;
        }
        
        .tts-indicator.error {
            background: var(--accent-color);
        }
        
        /* 阅读格式选择器模态框样式 */
        .format-picker-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 2000;
            /* 安全区域支持 */
            padding-left: var(--safe-area-inset-left);
            padding-right: var(--safe-area-inset-right);
            padding-top: var(--safe-area-inset-top);
            padding-bottom: var(--safe-area-inset-bottom));
        }
        
        .format-picker-modal.show {
            display: flex;
        }
        
        .format-picker-content {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 25px;
            box-shadow: var(--shadow);
            width: 90%;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
            margin: auto;
        }
        
        .format-picker-title {
            margin: 0 0 20px 0;
            font-size: 1.3em;
            color: var(--primary-color);
            text-align: center;
        }
        
        .format-presets {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        
        @media screen and (max-width: 768px) {
            .format-presets {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        @media screen and (max-width: 480px) {
            .format-presets {
                grid-template-columns: 1fr;
            }
        }
        
        .format-preset {
            background: var(--card-bg);
            border: 2px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
        }
        
        .format-preset:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow);
        }
        
        .format-preset.active {
            border-color: var(--secondary-color);
            background: rgba(52, 152, 219, 0.1);
        }
        
        .format-icon {
            font-size: 2em;
            margin-bottom: 10px;
            color: var(--secondary-color);
        }
        
        .format-name {
            font-weight: 600;
            margin-bottom: 5px;
            color: var(--primary-color);
        }
        
        .format-desc {
            font-size: 0.8em;
            color: var(--text-color);
            opacity: 0.7;
        }
        
        .format-picker-actions {
            display: flex;
            gap: 10px;
            justify-content: space-between;
        }
        
        .format-picker-btn {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 6px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .format-picker-btn.apply {
            background: var(--secondary-color);
            color: white;
        }
        
        .format-picker-btn.cancel {
            background: var(--border-color);
            color: var(--text-color);
        }
        
        .format-picker-btn:hover {
            opacity: 0.9;
            transform: translateY(-2px);
        }

        /* 滚动控制面板样式 */
        .scroll-control-panel {
            position: fixed;
            right: 15px;
            bottom: 100px;
            background: rgba(255, 255, 255, 0.85);
            border: 1px solid rgba(224, 214, 200, 0.6);
            border-radius: 20px;
            padding: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            z-index: 999;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            opacity: 1;
            transform: translateX(0);
            /* 安全区域支持 */
            right: calc(15px + var(--safe-area-inset-right));
            bottom: calc(100px + var(--safe-area-inset-bottom));
        }
        
        .dark-mode .scroll-control-panel {
            background: rgba(45, 45, 45, 0.85);
            border-color: rgba(68, 68, 68, 0.6);
        }
        
        .scroll-control-panel.hidden {
            opacity: 0;
            transform: translateX(100px);
            pointer-events: none;
        }
        
        .scroll-control-panel.compact {
            padding: 8px;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.75);
        }
        
        .dark-mode .scroll-control-panel.compact {
            background: rgba(45, 45, 45, 0.75);
        }
        
        .scroll-controls {
            display: flex;
            flex-direction: column;
            gap: 6px;
            align-items: center;
        }
        
        .scroll-controls.compact {
            gap: 4px;
        }
        
        .scroll-btn {
            width: 40px;
            height: 40px;
            border: 1px solid var(--border-color);
            background: var(--card-bg);
            color: var(--text-color);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 1.1em;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            -webkit-tap-highlight-color: transparent;
        }
        
        .scroll-controls.compact .scroll-btn {
            width: 36px;
            height: 36px;
            font-size: 1em;
        }
        
        .scroll-btn:hover {
            background-color: var(--secondary-color);
            color: white;
            transform: scale(1.08);
            box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
        }
        
        .scroll-btn:active {
            transform: scale(0.95);
        }
        
        .scroll-btn.back-to-top {
            background: var(--accent-color);
            color: white;
            border-color: var(--accent-color);
        }
        
        .scroll-btn.back-to-top:hover {
            background: #c0392b;
            border-color: #c0392b;
        }
        
        .scroll-speed-control {
            display: flex;
            align-items: center;
            gap: 6px;
            margin: 4px 0;
            padding: 4px 8px;
            background: rgba(0, 0, 0, 0.05);
            border-radius: 12px;
        }
        
        .dark-mode .scroll-speed-control {
            background: rgba(255, 255, 255, 0.05);
        }
        
        .scroll-controls.compact .scroll-speed-control {
            display: none;
        }
        
        .speed-label {
            font-size: 0.75em;
            color: var(--text-color);
            white-space: nowrap;
            opacity: 0.8;
        }
        
        .speed-display {
            font-size: 0.85em;
            font-weight: bold;
            color: var(--secondary-color);
            min-width: 20px;
            text-align: center;
        }
        
        .speed-btn {
            width: 24px;
            height: 24px;
            border: 1px solid var(--border-color);
            background: var(--card-bg);
            color: var(--text-color);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 0.8em;
            transition: all 0.2s ease;
        }
        
        .speed-btn:hover {
            background-color: var(--secondary-color);
            color: white;
        }
        
        /* TTS语音控制面板样式 */
        .tts-control-panel {
            position: fixed;
            left: 15px;
            bottom: 100px;
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid rgba(224, 214, 200, 0.8);
            border-radius: 20px;
            padding: 15px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            z-index: 998;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            opacity: 1;
            transform: translateX(0);
            min-width: 200px;
            /* 安全区域支持 */
            left: calc(15px + var(--safe-area-inset-left));
            bottom: calc(100px + var(--safe-area-inset-bottom));
        }
        
        .dark-mode .tts-control-panel {
            background: rgba(45, 45, 45, 0.95);
            border-color: rgba(68, 68, 68, 0.8);
        }
        
        .tts-control-panel.hidden {
            opacity: 0;
            transform: translateX(-100px);
            pointer-events: none;
        }
        
        .tts-controls {
            display: flex;
            flex-direction: column;
            gap: 10px;
            align-items: center;
        }
        
        .tts-btn {
            width: 44px;
            height: 44px;
            border: 1px solid var(--border-color);
            background: var(--card-bg);
            color: var(--text-color);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 1.2em;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            -webkit-tap-highlight-color: transparent;
        }
        
        .tts-btn:hover {
            background-color: var(--secondary-color);
            color: white;
            transform: scale(1.08);
            box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
        }
        
        .tts-btn:active {
            transform: scale(0.95);
        }
        
        .tts-btn.active {
            background-color: var(--accent-color);
            color: white;
            border-color: var(--accent-color);
        }
        
        .tts-btn.active:hover {
            background-color: #c0392b;
            border-color: #c0392b;
        }
        
        .tts-speed-control {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 5px 0;
            padding: 6px 10px;
            background: rgba(0, 0, 0, 0.05);
            border-radius: 15px;
            width: 100%;
            justify-content: space-between;
        }
        
        .dark-mode .tts-speed-control {
            background: rgba(255, 255, 255, 0.05);
        }
        
        .tts-speed-label {
            font-size: 0.8em;
            color: var(--text-color);
            white-space: nowrap;
            opacity: 0.8;
        }
        
        .tts-speed-display {
            font-size: 0.9em;
            font-weight: bold;
            color: var(--secondary-color);
            min-width: 20px;
            text-align: center;
        }
        
        .tts-speed-btn {
            width: 26px;
            height: 26px;
            border: 1px solid var(--border-color);
            background: var(--card-bg);
            color: var(--text-color);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 0.8em;
            transition: all 0.2s ease;
        }
        
        .tts-speed-btn:hover {
            background-color: var(--secondary-color);
            color: white;
        }
        
        .tts-voice-select {
            width: 100%;
            padding: 6px 10px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: var(--card-bg);
            color: var(--text-color);
            font-size: 0.8em;
            margin-top: 5px;
        }
        
        /* 高亮当前朗读文本 */
        .tts-highlight {
            background-color: rgba(52, 152, 219, 0.3);
            border-radius: 3px;
            padding: 2px 1px;
            transition: background-color 0.3s ease;
        }

        /* 图片查看样式 */
        .image-container {
            text-align: center;
            padding: 20px;
        }
        
        .image-preview {
            max-width: 100%;
            max-height: 80vh;
            border-radius: 10px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            border: 3px solid var(--border-color);
        }
        
        .image-info {
            margin-top: 15px;
            padding: 15px;
            background: var(--card-bg);
            border-radius: 8px;
            box-shadow: var(--shadow);
        }
        
        .image-meta {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }
        
        .meta-item {
            text-align: center;
            padding: 8px;
            background: rgba(0, 0, 0, 0.05);
            border-radius: 6px;
            font-size: 0.9em;
        }
        
        .dark-mode .meta-item {
            background: rgba(255, 255, 255, 0.05);
        }
        
        /* 电子书提示样式 */
        .ebook-notice {
            text-align: center;
            padding: 40px 20px;
            background: var(--card-bg);
            border-radius: 10px;
            box-shadow: var(--shadow);
            margin: 20px 0;
        }
        
        .ebook-icon {
            font-size: 3em;
            color: var(--secondary-color);
            margin-bottom: 20px;
        }
        
        .ebook-actions {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .ebook-btn {
            padding: 10px 20px;
            border: 1px solid var(--border-color);
            background: var(--card-bg);
            color: var(--text-color);
            border-radius: 6px;
            text-decoration: none;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .ebook-btn:hover {
            background: var(--secondary-color);
            color: white;
            transform: translateY(-2px);
        }

        .back-button {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin: 10px 0 20px 0;
            padding: 10px 18px;
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            border-radius: 6px;
            font-size: 1em;
            text-decoration: none;
            box-shadow: var(--shadow);
            transition: all 0.2s;
            -webkit-tap-highlight-color: transparent;
        }
        
        /* 触摸设备按钮优化 */
        @media (hover: none) and (pointer: coarse) {
            .back-button:hover, .ebook-btn:hover {
                transform: none;
                background-color: var(--card-bg);
            }
            
            .back-button:active, .ebook-btn:active {
                background-color: rgba(0,0,0,0.03);
                transform: scale(0.98);
            }
            
            .dark-mode .back-button:active, 
            .dark-mode .ebook-btn:active {
                background-color: rgba(255,255,255,0.05);
            }
        }
        
        /* 非触摸设备悬停效果 */
        @media (hover: hover) {
            .back-button:hover, .ebook-btn:hover {
                background-color: rgba(0,0,0,0.03);
                transform: translateY(-2px);
            }
            
            .dark-mode .back-button:hover, 
            .dark-mode .ebook-btn:hover {
                background-color: rgba(255,255,255,0.05);
            }
        }
        
        /* 键盘导航优化 */
        .control-btn:focus-visible,
        .back-button:focus-visible,
        .scroll-btn:focus-visible,
        .tts-btn:focus-visible,
        .pdf-btn:focus-visible,
        .zoom-btn:focus-visible {
            outline: 2px solid var(--secondary-color);
            outline-offset: 2px;
        }
        
        /* 超小屏幕手机优化 (小于 360px) */
        @media screen and (max-width: 359px) {
            .container {
                padding: 12px;
                padding-left: calc(12px + var(--safe-area-inset-left));
                padding-right: calc(12px + var(--safe-area-inset-right));
                padding-bottom: calc(12px + var(--safe-area-inset-bottom));
            }
            
            .header {
                padding: 10px 12px;
                padding-left: calc(12px + var(--safe-area-inset-left));
                padding-right: calc(12px + var(--safe-area-inset-right));
                padding-top: calc(10px + var(--safe-area-inset-top));
            }
            
            .header h1 {
                font-size: 1.1em;
                max-width: 35%;
            }
            
            .control-btn {
                width: 30px;
                height: 30px;
                font-size: 0.9em;
            }
            
            .controls {
                gap: 5px;
            }
            
            .format-presets {
                grid-template-columns: 1fr;
            }
            
            .ebook-actions {
                flex-direction: column;
            }
            
            .scroll-control-panel {
                right: 8px;
                bottom: 80px;
                right: calc(8px + var(--safe-area-inset-right));
                bottom: calc(80px + var(--safe-area-inset-bottom));
            }
            
            .tts-control-panel {
                left: 8px;
                bottom: 80px;
                left: calc(8px + var(--safe-area-inset-left));
                bottom: calc(80px + var(--safe-area-inset-bottom));
                min-width: 180px;
            }
            
            .pdf-controls {
                gap: 6px;
            }
            
            .pdf-btn {
                padding: 6px 10px;
                font-size: 0.75em;
            }
            
            .pdf-page-info {
                min-width: 70px;
                font-size: 0.75em;
            }
            
            .font-indicator, .format-indicator {
                right: calc(12px + var(--safe-area-inset-right));
                bottom: calc(12px + var(--safe-area-inset-bottom));
            }
            
            .format-indicator {
                bottom: calc(60px + var(--safe-area-inset-bottom));
            }
        }
        
        /* 手机横屏适配 (480px - 767px) */
        @media screen and (min-width: 480px) and (max-width: 767px) {
            .header h1 {
                font-size: 1.5em;
                max-width: 55%;
            }
            
            .pdf-controls {
                gap: 12px;
            }
        }
        
        /* 平板竖屏适配 (768px - 1024px) */
        @media screen and (min-width: 768px) and (max-width: 1024px) {
            .container {
                width: 95%;
                padding: 25px;
                padding-left: calc(25px + var(--safe-area-inset-left));
                padding-right: calc(25px + var(--safe-area-inset-right));
            }
            
            .header {
                padding: 15px 25px;
                padding-left: calc(25px + var(--safe-area-inset-left));
                padding-right: calc(25px + var(--safe-area-inset-right));
            }
            
            .header h1 {
                font-size: 1.6em;
                max-width: 60%;
            }
            
            .scroll-control-panel {
                right: 20px;
                bottom: 120px;
            }
            
            .tts-control-panel {
                left: 20px;
                bottom: 120px;
            }
        }
        
        /* 平板横屏优化 (768px - 1024px) */
        @media screen and (min-width: 768px) and (max-width: 1024px) and (orientation: landscape) {
            .container {
                padding: 20px;
            }
            
            .header h1 {
                max-width: 60%;
            }
        }
        
        /* 桌面适配 (1025px - 1199px) */
        @media screen and (min-width: 1025px) and (max-width: 1199px) {
            .container {
                width: 90%;
                max-width: 1200px;
                padding: 30px;
            }
        }
        
        /* 大屏桌面优化 (大于 1200px) */
        @media screen and (min-width: 1200px) {
            .container {
                max-width: 1400px;
                padding: 35px;
            }
            
            .scroll-control-panel {
                right: 25px;
                bottom: 150px;
            }
            
            .tts-control-panel {
                left: 25px;
                bottom: 150px;
            }
        }
        
        /* 折叠屏设备支持 */
        @media (spanning: single-fold-vertical) {
            .container {
                padding: 20px;
                margin: 0 env(fold-left, 0px) 0 env(fold-right, 0px);
            }
        }
        
        /* 高DPI屏幕优化 */
        @media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
            .control-btn, .back-button, .scroll-btn, .tts-btn, .pdf-btn, .zoom-btn {
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }
        }

        /* 防止长按选择文本 */
        .chapter-content {
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
            user-select: none;
        }
        
        /* 透明度减少偏好 */
        @media (prefers-reduced-transparency: reduce) {
            .scroll-control-panel, .tts-control-panel {
                backdrop-filter: none;
                -webkit-backdrop-filter: none;
                background: var(--card-bg);
            }
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
</head>
<body class="font-medium" data-format="<?php echo $format; ?>">
    
    <!-- 字体大小指示器 -->
    <div class="font-indicator" id="fontIndicator">字体大小: 中</div>
    
    <!-- 阅读格式指示器 -->
    <div class="format-indicator" id="formatIndicator">阅读格式已更改</div>
    
    <!-- 自动滚动指示器 -->
    <div class="auto-scroll-indicator" id="autoScrollIndicator">自动滚动中...</div>
    
    <!-- TTS状态指示器 -->
    <div class="tts-indicator" id="ttsIndicator">语音朗读准备就绪</div>
    
    <!-- 阅读格式选择器模态框 -->
    <div class="format-picker-modal" id="formatPickerModal">
        <div class="format-picker-content">
            <h3 class="format-picker-title">选择阅读格式</h3>
            
            <div class="format-presets">
                <div class="format-preset" data-format="default">
                    <div class="format-icon"><i class="fas fa-book-open"></i></div>
                    <div class="format-name">默认模式</div>
                    <div class="format-desc">舒适阅读体验，优化字体排版</div>
                </div>
                
                <div class="format-preset" data-format="page">
                    <div class="format-icon"><i class="fas fa-columns"></i></div>
                    <div class="format-name">分页模式</div>
                    <div class="format-desc">多栏分页显示，类似报纸排版</div>
                </div>
                
                <div class="format-preset" data-format="comic">
                    <div class="format-icon"><i class="fas fa-mask"></i></div>
                    <div class="format-name">漫画模式</div>
                    <div class="format-desc">趣味漫画风格，适合轻松阅读</div>
                </div>
                
                <div class="format-preset" data-format="classic">
                    <div class="format-icon"><i class="fas fa-scroll"></i></div>
                    <div class="format-name">经典模式</div>
                    <div class="format-desc">仿古书籍排版，传统阅读体验</div>
                </div>
                
                <div class="format-preset" data-format="modern">
                    <div class="format-icon"><i class="fas fa-mobile-alt"></i></div>
                    <div class="format-name">现代模式</div>
                    <div class="format-desc">简洁现代设计，适合移动设备</div>
                </div>
                
                <!-- 新增的阅读格式 -->
                <div class="format-preset" data-format="professional">
                    <div class="format-icon"><i class="fas fa-user-tie"></i></div>
                    <div class="format-name">专业模式</div>
                    <div class="format-desc">学术论文风格，适合专业阅读</div>
                </div>
                
                <div class="format-preset" data-format="eye-care">
                    <div class="format-icon"><i class="fas fa-eye"></i></div>
                    <div class="format-name">护眼模式</div>
                    <div class="format-desc">绿色背景，缓解视觉疲劳</div>
                </div>
                
                <div class="format-preset" data-format="dark-eye-care">
                    <div class="format-icon"><i class="fas fa-moon"></i></div>
                    <div class="format-name">黑暗护眼</div>
                    <div class="format-desc">深色背景，夜间阅读更舒适</div>
                </div>
                
                <div class="format-preset" data-format="magazine">
                    <div class="format-icon"><i class="fas fa-newspaper"></i></div>
                    <div class="format-name">杂志模式</div>
                    <div class="format-desc">杂志风格排版，多栏显示</div>
                </div>
            </div>
            
            <div class="format-picker-actions">
                <button class="format-picker-btn cancel" id="cancelFormatBtn">取消</button>
                <button class="format-picker-btn apply" id="applyFormatBtn">应用格式</button>
            </div>
        </div>
    </div>
    
    <?php if ($fileType === 'text'): ?>
    <!-- 滚动控制面板 - 只在文本阅读页面显示 -->
    <div class="scroll-control-panel" id="scrollControlPanel">
        <div class="scroll-controls" id="scrollControls">
            <!-- 一键返回顶部 -->
            <button class="scroll-btn back-to-top" id="backToTopBtn" title="返回顶部">
                <i class="fas fa-arrow-up"></i>
            </button>
            
            <!-- 速度控制 -->
            <div class="scroll-speed-control">
                <span class="speed-label">速度</span>
                <button class="speed-btn" id="speedDownBtn" title="减慢">
                    <i class="fas fa-minus"></i>
                </button>
                <span class="speed-display" id="speedDisplay">2</span>
                <button class="speed-btn" id="speedUpBtn" title="加快">
                    <i class="fas fa-plus"></i>
                </button>
            </div>
            
            <!-- 滚动控制按钮 -->
            <button class="scroll-btn" id="scrollPauseBtn" title="暂停滚动">
                <i class="fas fa-pause"></i>
            </button>
            <button class="scroll-btn" id="scrollPlayBtn" title="开始滚动">
                <i class="fas fa-play"></i>
            </button>
            <button class="scroll-btn" id="scrollStopBtn" title="停止滚动">
                <i class="fas fa-stop"></i>
            </button>
        </div>
    </div>
    <?php endif; ?>
    
    <!-- TTS语音控制面板 -->
    <div class="tts-control-panel hidden" id="ttsControlPanel">
        <div class="tts-controls" id="ttsControls">
            <!-- 语音选择 -->
            <select class="tts-voice-select" id="ttsVoiceSelect">
                <option value="">选择语音...</option>
            </select>
            
            <!-- 速度控制 -->
            <div class="tts-speed-control">
                <span class="tts-speed-label">语速</span>
                <button class="tts-speed-btn" id="ttsSpeedDownBtn" title="减慢语速">
                    <i class="fas fa-minus"></i>
                </button>
                <span class="tts-speed-display" id="ttsSpeedDisplay">1</span>
                <button class="tts-speed-btn" id="ttsSpeedUpBtn" title="加快语速">
                    <i class="fas fa-plus"></i>
                </button>
            </div>
            
            <!-- 控制按钮 -->
            <div style="display: flex; gap: 8px; justify-content: center; width: 100%;">
                <button class="tts-btn" id="ttsPlayBtn" title="开始朗读">
                    <i class="fas fa-play"></i>
                </button>
                <button class="tts-btn" id="ttsPauseBtn" title="暂停朗读" style="display: none;">
                    <i class="fas fa-pause"></i>
                </button>
                <button class="tts-btn" id="ttsStopBtn" title="停止朗读">
                    <i class="fas fa-stop"></i>
                </button>
            </div>
            
            <!-- 朗读范围选择 -->
            <div style="display: flex; gap: 5px; width: 100%;">
                <button class="tts-speed-btn" id="ttsCurrentBtn" title="朗读当前段落" style="flex: 1; border-radius: 8px; font-size: 0.7em;">
                    当前段
                </button>
                <button class="tts-speed-btn" id="ttsChapterBtn" title="朗读整章" style="flex: 1; border-radius: 8px; font-size: 0.7em;">
                    整章
                </button>
            </div>
        </div>
    </div>
    
    <!-- 头部控制栏 -->
    <div class="header">
        <h1><?php echo htmlspecialchars($chapterTitle); ?></h1>
        <div class="controls">
            <?php if ($fileType === 'text'): ?>
                <button class="control-btn" id="format-btn" title="切换阅读格式">
                    <i class="fas fa-palette"></i>
                </button>
                <button class="control-btn" id="font-size-btn" title="调整字体大小">
                    <i class="fas fa-text-height"></i>
                </button>
                <button class="control-btn" id="tts-toggle-btn" title="语音朗读">
                    <i class="fas fa-volume-up"></i>
                </button>
            <?php endif; ?>
            <button class="control-btn" id="dark-mode-btn" title="切换夜间模式">
                <i class="fas fa-moon"></i>
            </button>
        </div>
    </div>
    
    <div class="container">
        <!-- 返回按钮 -->
        <a href="index.php<?php 
            echo $file ? '?file=' . urlencode($file) : ''; 
            echo $format !== 'default' ? '&format=' . urlencode($format) : ''; 
        ?>" class="back-button">
            <i class="fas fa-arrow-left"></i>
            返回文件列表
        </a>
        
        <?php if ($fileType === 'text'): ?>
            <!-- 文本内容 -->
            <div class="chapter-content" id="chapterContent">
                <?php 
                // 格式化内容，确保段落显示
                $formattedContent = preg_replace('/(\r\n|\r|\n){2,}/', "\n\n", $chapterContent);
                $paragraphs = explode("\n\n", $formattedContent);
                
                foreach ($paragraphs as $paragraph) {
                    if (trim($paragraph) !== '') {
                        echo '<p>' . nl2br(htmlspecialchars(trim($paragraph))) . '</p>';
                    }
                }
                ?>
            </div>
            
            <div class="loading" id="loading" style="display: none;">加载中...</div>
            
        <?php elseif ($fileType === 'image'): ?>
            <!-- 图片内容 -->
            <div class="image-container">
                <img src="<?php echo $imageData; ?>" 
                     alt="<?php echo htmlspecialchars($chapterTitle); ?>" 
                     class="image-preview"
                     onload="this.style.opacity='1'"
                     style="opacity:0;transition:opacity 0.3s">
                
                <div class="image-info">
                    <h3>图片信息</h3>
                    <div class="image-meta">
                        <div class="meta-item">
                            <strong>文件名</strong><br>
                            <?php echo htmlspecialchars($fileInfo['filename'] . '.' . $fileInfo['extension']); ?>
                        </div>
                        <div class="meta-item">
                            <strong>尺寸</strong><br>
                            <?php echo $imageWidth . ' × ' . $imageHeight; ?> 像素
                        </div>
                        <div class="meta-item">
                            <strong>格式</strong><br>
                            <?php echo strtoupper($fileInfo['extension']); ?>
                        </div>
                    </div>
                </div>
            </div>
            
        <?php elseif ($isPdf): ?>
            <!-- PDF阅读器 -->
            <div class="pdf-container">
                <div class="pdf-controls">
                    <button class="pdf-btn" id="pdfPrevBtn">
                        <i class="fas fa-chevron-left"></i> 上一页
                    </button>
                    
                    <div class="pdf-page-info">
                        <span id="pdfPageInfo">页面: 0 / 0</span>
                    </div>
                    
                    <button class="pdf-btn" id="pdfNextBtn">
                        下一页 <i class="fas fa-chevron-right"></i>
                    </button>
                    
                    <input type="number" id="pdfPageInput" class="pdf-page-input" min="1" value="1">
                    <button class="pdf-btn" id="pdfGoBtn">跳转</button>
                    
                    <div class="pdf-zoom-controls">
                        <button class="zoom-btn" id="pdfZoomOutBtn" title="缩小">
                            <i class="fas fa-search-minus"></i>
                        </button>
                        <span class="zoom-display" id="pdfZoomDisplay">100%</span>
                        <button class="zoom-btn" id="pdfZoomInBtn" title="放大">
                            <i class="fas fa-search-plus"></i>
                        </button>
                        <button class="pdf-btn" id="pdfFitWidthBtn" title="适应宽度">
                            <i class="fas fa-arrows-alt-h"></i>
                        </button>
                        <button class="pdf-btn" id="pdfFitPageBtn" title="适应页面">
                            <i class="fas fa-arrows-alt"></i>
                        </button>
                    </div>
                    
                    <button class="pdf-btn" id="pdfDownloadBtn" title="下载PDF">
                        <i class="fas fa-download"></i> 下载
                    </button>
                </div>
                
                <div class="pdf-viewer" id="pdfViewer">
                    <div class="pdf-loading" id="pdfLoading">
                        <i class="fas fa-spinner fa-spin"></i><br>
                        正在加载PDF文档...
                    </div>
                    <div class="pdf-error" id="pdfError" style="display: none;"></div>
                    <canvas id="pdfCanvas"></canvas>
                </div>
            </div>
            
        <?php else: ?>
            <!-- 电子书内容 -->
            <div class="ebook-notice">
                <div class="ebook-icon">
                    <i class="fas fa-book"></i>
                </div>
                <h2><?php echo htmlspecialchars($chapterTitle); ?></h2>
                <p><?php echo $chapterContent; ?></p>
                <p>文件格式: <strong><?php echo strtoupper($fileExtension); ?></strong></p>
                <p class="chapter-meta">建议在电脑端使用专用阅读器打开此文件</p>
                
                <div class="ebook-actions">
                    <a href="xs/<?php echo urlencode($file); ?>" class="ebook-btn" download>
                        <i class="fas fa-download"></i>
                        下载文件
                    </a>
                    <a href="index.php" class="ebook-btn">
                        <i class="fas fa-arrow-left"></i>
                        返回列表
                    </a>
                </div>
            </div>
        <?php endif; ?>
    </div>

    <script>
        // ========== PDF阅读功能 ==========
        <?php if ($isPdf): ?>
        let pdfDoc = null;
        let pageNum = 1;
        let pageRendering = false;
        let pageNumPending = null;
        let scale = 1.0;
        const canvas = document.getElementById('pdfCanvas');
        const ctx = canvas.getContext('2d');
        
        // 渲染页面
        async function renderPage(num) {
            if (pageRendering) {
                pageNumPending = num;
                return;
            }
            
            pageRendering = true;
            pageNum = num;
            
            try {
                const page = await pdfDoc.getPage(num);
                const viewport = page.getViewport({ scale: scale });
                
                canvas.height = viewport.height;
                canvas.width = viewport.width;
                
                const renderContext = {
                    canvasContext: ctx,
                    viewport: viewport
                };
                
                await page.render(renderContext).promise;
                document.getElementById('pdfPageInfo').textContent = `页面: ${pageNum} / ${pdfDoc.numPages}`;
                document.getElementById('pdfPageInput').value = pageNum;
                document.getElementById('pdfZoomDisplay').textContent = Math.round(scale * 100) + '%';
                
                pageRendering = false;
                
                if (pageNumPending !== null) {
                    renderPage(pageNumPending);
                    pageNumPending = null;
                }
                
            } catch (err) {
                console.error('页面渲染错误:', err);
                pageRendering = false;
            }
        }
        
        // 上一页
        function prevPage() {
            if (pageNum <= 1) return;
            renderPage(pageNum - 1);
        }
        
        // 下一页
        function nextPage() {
            if (pageNum >= pdfDoc.numPages) return;
            renderPage(pageNum + 1);
        }
        
        // 跳转到指定页面
        function goToPage() {
            const input = document.getElementById('pdfPageInput');
            const page = parseInt(input.value);
            
            if (page >= 1 && page <= pdfDoc.numPages) {
                renderPage(page);
            } else {
                input.value = pageNum;
            }
        }
        
        // 缩放控制
        function zoomIn() {
            scale += 0.1;
            renderPage(pageNum);
        }
        
        function zoomOut() {
            if (scale <= 0.2) return;
            scale -= 0.1;
            renderPage(pageNum);
        }
        
        // 适应宽度
        function fitToWidth() {
            const container = document.getElementById('pdfViewer');
            const containerWidth = container.clientWidth - 40; // 减去padding
            
            pdfDoc.getPage(pageNum).then(page => {
                const viewport = page.getViewport({ scale: 1.0 });
                scale = containerWidth / viewport.width;
                renderPage(pageNum);
            });
        }
        
        // 适应页面
        function fitToPage() {
            const container = document.getElementById('pdfViewer');
            const containerWidth = container.clientWidth - 40;
            const containerHeight = container.clientHeight - 40;
            
            pdfDoc.getPage(pageNum).then(page => {
                const viewport = page.getViewport({ scale: 1.0 });
                const scaleX = containerWidth / viewport.width;
                const scaleY = containerHeight / viewport.height;
                scale = Math.min(scaleX, scaleY);
                renderPage(pageNum);
            });
        }
        
        // 下载PDF
        function downloadPDF() {
            const link = document.createElement('a');
            link.href = "<?php echo $pdfFilePath; ?>";
            link.download = "<?php echo $fileInfo['filename'] . '.pdf'; ?>";
            link.click();
        }
        
        // 事件绑定
        document.getElementById('pdfPrevBtn').addEventListener('click', prevPage);
        document.getElementById('pdfNextBtn').addEventListener('click', nextPage);
        document.getElementById('pdfGoBtn').addEventListener('click', goToPage);
        document.getElementById('pdfZoomInBtn').addEventListener('click', zoomIn);
        document.getElementById('pdfZoomOutBtn').addEventListener('click', zoomOut);
        document.getElementById('pdfFitWidthBtn').addEventListener('click', fitToWidth);
        document.getElementById('pdfFitPageBtn').addEventListener('click', fitToPage);
        document.getElementById('pdfDownloadBtn').addEventListener('click', downloadPDF);
        
        // 输入框回车事件
        document.getElementById('pdfPageInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                goToPage();
            }
        });
        
        // 修改PDF加载部分
        (async function(){
            // 使用正确的相对路径
            const pdfPath = "<?php echo $pdfFilePath; ?>";
            const loading = document.getElementById('pdfLoading');
            const error = document.getElementById('pdfError');
            
            try {
                loading.style.display = 'block';
                console.log('正在加载PDF:', pdfPath);
                
                // 使用正确的PDF.js配置
                const loadingTask = pdfjsLib.getDocument({
                    url: pdfPath,
                    cMapUrl: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/cmaps/',
                    cMapPacked: true,
                });
                
                pdfDoc = await loadingTask.promise;
                
                document.getElementById('pdfPageInfo').textContent = `页面: 1 / ${pdfDoc.numPages}`;
                document.getElementById('pdfPageInput').max = pdfDoc.numPages;
                
                // 渲染第一页
                await renderPage(1);
                loading.style.display = 'none';
                
            } catch (err) {
                loading.style.display = 'none';
                error.style.display = 'block';
                error.innerHTML = `
                    <i class="fas fa-exclamation-triangle"></i><br>
                    PDF加载失败<br>
                    错误: ${err.message}<br>
                    路径: ${pdfPath}<br>
                    <small>请检查文件是否存在且路径正确</small>
                `;
                console.error('PDF加载详细错误:', err);
                
                // 提供下载链接
                const downloadLink = document.createElement('a');
                downloadLink.href = pdfPath;
                downloadLink.textContent = '点击下载PDF文件';
                downloadLink.download = '';
                downloadLink.style.display = 'block';
                downloadLink.style.marginTop = '10px';
                error.appendChild(downloadLink);
            }
        })();
        <?php endif; ?>
        
        // ========== 多格式阅读功能 ==========
        <?php if ($fileType === 'text'): ?>
        
        const formatBtn = document.getElementById('format-btn');
        const formatPickerModal = document.getElementById('formatPickerModal');
        const formatPresets = document.querySelectorAll('.format-preset');
        const applyFormatBtn = document.getElementById('applyFormatBtn');
        const cancelFormatBtn = document.getElementById('cancelFormatBtn');
        const formatIndicator = document.getElementById('formatIndicator');
        
        let currentFormat = '<?php echo $format; ?>';
        let selectedFormat = currentFormat;
        
        // 初始化阅读格式
        function initReadingFormat() {
            // 优先级：URL参数 > 本地存储 > PHP默认值
            const urlParams = new URLSearchParams(window.location.search);
            const urlFormat = urlParams.get('format');
            
            if (urlFormat && urlFormat !== currentFormat) {
                currentFormat = urlFormat;
            } else {
                const savedFormat = localStorage.getItem('preferredReadingFormat');
                if (savedFormat && savedFormat !== currentFormat) {
                    currentFormat = savedFormat;
                }
            }
            
            // 应用格式
            applyFormat(currentFormat);
            
            // 持久化保存
            localStorage.setItem('preferredReadingFormat', currentFormat);
            document.cookie = `preferredReadingFormat=${currentFormat}; path=/; max-age=31536000`;
            
            // 更新URL但不刷新页面
            updateUrlParameter('format', currentFormat);
            
            // 高亮当前格式
            formatPresets.forEach(preset => {
                preset.classList.toggle('active', preset.dataset.format === currentFormat);
            });
            
            console.log('阅读格式已初始化为:', currentFormat);
        }
        
        // 应用格式到页面
        function applyFormat(format) {
            document.body.setAttribute('data-format', format);
            document.body.className = document.body.className.replace(/\bformat-\w+/g, '');
            document.body.classList.add('format-' + format);
            currentFormat = format;
        }
        
        // 更新URL参数
        function updateUrlParameter(key, value) {
            const url = new URL(window.location);
            url.searchParams.set(key, value);
            window.history.replaceState({}, '', url);
        }
        
        // 显示格式选择器
        formatBtn.addEventListener('click', function() {
            selectedFormat = currentFormat;
            formatPresets.forEach(preset => {
                preset.classList.toggle('active', preset.dataset.format === selectedFormat);
            });
            formatPickerModal.classList.add('show');
        });
        
        // 选择格式预设
        formatPresets.forEach(preset => {
            preset.addEventListener('click', function() {
                selectedFormat = this.dataset.format;
                formatPresets.forEach(p => p.classList.remove('active'));
                this.classList.add('active');
            });
        });
        
        // 应用格式
        applyFormatBtn.addEventListener('click', function() {
            if (selectedFormat !== currentFormat) {
                applyFormat(selectedFormat);
                localStorage.setItem('preferredReadingFormat', selectedFormat);
                document.cookie = `preferredReadingFormat=${selectedFormat}; path=/; max-age=31536000`;
                updateUrlParameter('format', selectedFormat);
                showFormatIndicator('已切换到' + getFormatName(selectedFormat) + '模式');
            }
            formatPickerModal.classList.remove('show');
        });
        
        // 取消选择
        cancelFormatBtn.addEventListener('click', function() {
            formatPickerModal.classList.remove('show');
        });
        
        // 点击模态框外部关闭
        formatPickerModal.addEventListener('click', function(e) {
            if (e.target === formatPickerModal) {
                formatPickerModal.classList.remove('show');
            }
        });
        
        // 获取格式名称 - 添加新的格式名称
        function getFormatName(format) {
            const names = {
                'default': '默认',
                'page': '分页',
                'comic': '漫画',
                'classic': '经典',
                'modern': '现代',
                'professional': '专业',
                'eye-care': '护眼',
                'dark-eye-care': '黑暗护眼',
                'magazine': '杂志'
            };
            return names[format] || '默认';
        }
        
        // 显示格式指示器
        function showFormatIndicator(message) {
            formatIndicator.textContent = message;
            formatIndicator.classList.add('show');
            setTimeout(() => {
                formatIndicator.classList.remove('show');
            }, 2000);
        }
        
        // ========== 滚动控制功能 ==========
        
        let isProgrammaticScroll = false;
        let isTTSActive = false;
        
        // 滚动控制功能
        const scrollControlPanel = document.getElementById('scrollControlPanel');
        const scrollControls = document.getElementById('scrollControls');
        const backToTopBtn = document.getElementById('backToTopBtn');
        const scrollPauseBtn = document.getElementById('scrollPauseBtn');
        const scrollPlayBtn = document.getElementById('scrollPlayBtn');
        const scrollStopBtn = document.getElementById('scrollStopBtn');
        const speedDownBtn = document.getElementById('speedDownBtn');
        const speedUpBtn = document.getElementById('speedUpBtn');
        const speedDisplay = document.getElementById('speedDisplay');
        const autoScrollIndicator = document.getElementById('autoScrollIndicator');
        
        let autoScrollInterval = null;
        let scrollSpeed = parseInt(localStorage.getItem('scrollSpeed')) || 2;
        let isAutoScrolling = false;
        let hidePanelTimeout = null;
        let scrollTimeout = null;

        // 初始化滚动速度
        function initScrollSpeed() {
            speedDisplay.textContent = scrollSpeed;
        }
        
        // 返回顶部
        backToTopBtn.addEventListener('click', function() {
            isProgrammaticScroll = true;
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
            setTimeout(() => { isProgrammaticScroll = false; }, 500);
        });
        
        // 速度控制
        speedDownBtn.addEventListener('click', function() {
            if (scrollSpeed > 1) {
                scrollSpeed--;
                speedDisplay.textContent = scrollSpeed;
                localStorage.setItem('scrollSpeed', scrollSpeed);
                if (isAutoScrolling) {
                    stopAutoScroll();
                    startAutoScroll();
                }
            }
        });
        
        speedUpBtn.addEventListener('click', function() {
            if (scrollSpeed < 10) {
                scrollSpeed++;
                speedDisplay.textContent = scrollSpeed;
                localStorage.setItem('scrollSpeed', scrollSpeed);
                if (isAutoScrolling) {
                    stopAutoScroll();
                    startAutoScroll();
                }
            }
        });
        
        // 开始自动滚动
        function startAutoScroll() {
            if (autoScrollInterval) {
                clearInterval(autoScrollInterval);
            }
            
            autoScrollInterval = setInterval(() => {
                isProgrammaticScroll = true;
                window.scrollBy({
                    top: scrollSpeed,
                    behavior: 'smooth'
                });
                
                // 检查是否到达底部
                if ((window.innerHeight + window.pageYOffset) >= document.body.offsetHeight - 100) {
                    stopAutoScroll();
                    showAutoScrollIndicator('已到达底部');
                }
            }, 50);
            
            isAutoScrolling = true;
            scrollPlayBtn.style.display = 'none';
            scrollPauseBtn.style.display = 'flex';
            showAutoScrollIndicator('自动滚动中...');
            
            // 自动滚动启动时立即折叠面板，2秒后隐藏
            collapseAndHidePanel();
        }
        
        // 暂停自动滚动
        function pauseAutoScroll() {
            if (autoScrollInterval) {
                clearInterval(autoScrollInterval);
                autoScrollInterval = null;
            }
            isAutoScrolling = false;
            scrollPauseBtn.style.display = 'none';
            scrollPlayBtn.style.display = 'flex';
            showAutoScrollIndicator('已暂停');
            
            // 暂停时显示面板
            showPanel();
        }
        
        // 停止自动滚动
        function stopAutoScroll() {
            if (autoScrollInterval) {
                clearInterval(autoScrollInterval);
                autoScrollInterval = null;
            }
            isAutoScrolling = false;
            scrollPauseBtn.style.display = 'none';
            scrollPlayBtn.style.display = 'flex';
            showAutoScrollIndicator('已停止');
            
            // 停止时显示面板
            showPanel();
        }
        
        // 折叠和隐藏面板（自动滚动专用）
        function collapseAndHidePanel() {
            if (hidePanelTimeout) {
                clearTimeout(hidePanelTimeout);
            }
            
            // 立即折叠面板（贴边）
            scrollControlPanel.classList.add('compact');
            scrollControls.classList.add('compact');
            
            // 2秒后完全隐藏
            hidePanelTimeout = setTimeout(() => {
                scrollControlPanel.classList.add('hidden');
            }, 2000);
        }
        
        // 显示面板
        function showPanel() {
            if (hidePanelTimeout) {
                clearTimeout(hidePanelTimeout);
            }
            
            scrollControlPanel.classList.remove('hidden', 'compact');
            scrollControls.classList.remove('compact');
            
            // 如果不是自动滚动状态，重置自动隐藏计时器
            if (!isAutoScrolling) {
                resetHidePanelTimeout();
            }
        }
        
        // 显示自动滚动指示器
        function showAutoScrollIndicator(message) {
            autoScrollIndicator.textContent = message;
            autoScrollIndicator.classList.add('show');
            setTimeout(() => {
                autoScrollIndicator.classList.remove('show');
            }, 2000);
        }
        
        // 滚动控制按钮事件
        scrollPlayBtn.addEventListener('click', startAutoScroll);
        scrollPauseBtn.addEventListener('click', pauseAutoScroll);
        scrollStopBtn.addEventListener('click', stopAutoScroll);
        
        // 手动滚屏时的面板控制
        let isScrolling = false;
        
        function handleManualScroll() {
            if (isProgrammaticScroll || isTTSActive || isAutoScrolling) return;
            
            if (scrollTimeout) {
                clearTimeout(scrollTimeout);
            }
            
            scrollControlPanel.classList.add('compact');
            scrollControls.classList.add('compact');
            scrollControlPanel.classList.remove('hidden');
            
            isScrolling = true;
            
            scrollTimeout = setTimeout(() => {
                scrollControlPanel.classList.add('hidden');
                isScrolling = false;
            }, 2000);
        }
        
        const debouncedScrollHandler = debounce(handleManualScroll, 100);
        
        window.addEventListener('scroll', function() {
            if (!isAutoScrolling) {
                debouncedScrollHandler();
            }
        });
        
        // 控制面板自动隐藏
        function resetHidePanelTimeout() {
            if (hidePanelTimeout) {
                clearTimeout(hidePanelTimeout);
            }
            
            if (isAutoScrolling || isScrolling) {
                return;
            }
            
            scrollControlPanel.classList.remove('hidden', 'compact');
            scrollControls.classList.remove('compact');
            
            hidePanelTimeout = setTimeout(() => {
                scrollControlPanel.classList.add('compact');
                scrollControls.classList.add('compact');
                
                hidePanelTimeout = setTimeout(() => {
                    scrollControlPanel.classList.add('hidden');
                }, 2000);
            }, 2000);
        }
        
        // 鼠标进入控制面板时取消隐藏
        scrollControlPanel.addEventListener('mouseenter', function() {
            if (hidePanelTimeout) {
                clearTimeout(hidePanelTimeout);
            }
            if (scrollTimeout) {
                clearTimeout(scrollTimeout);
            }
            scrollControlPanel.classList.remove('hidden', 'compact');
            scrollControls.classList.remove('compact');
            isScrolling = false;
        });
        
        scrollControlPanel.addEventListener('mouseleave', resetHidePanelTimeout);
        document.addEventListener('mousemove', resetHidePanelTimeout);
        document.addEventListener('click', resetHidePanelTimeout);
        
        // ========== TTS语音朗读功能 ==========
        
        const ttsToggleBtn = document.getElementById('tts-toggle-btn');
        const ttsControlPanel = document.getElementById('ttsControlPanel');
        const ttsPlayBtn = document.getElementById('ttsPlayBtn');
        const ttsPauseBtn = document.getElementById('ttsPauseBtn');
        const ttsStopBtn = document.getElementById('ttsStopBtn');
        const ttsSpeedDownBtn = document.getElementById('ttsSpeedDownBtn');
        const ttsSpeedUpBtn = document.getElementById('ttsSpeedUpBtn');
        const ttsSpeedDisplay = document.getElementById('ttsSpeedDisplay');
        const ttsVoiceSelect = document.getElementById('ttsVoiceSelect');
        const ttsCurrentBtn = document.getElementById('ttsCurrentBtn');
        const ttsChapterBtn = document.getElementById('ttsChapterBtn');
        const ttsIndicator = document.getElementById('ttsIndicator');

        let ttsVoices = [];
        let ttsRate = parseFloat(localStorage.getItem('ttsRate')) || 1.0;
        let ttsVoiceURI = localStorage.getItem('ttsVoiceURI') || '';
        let isTTSEnabled = false;
        let currentUtterance = null;
        let currentParagraphIndex = 0;
        let paragraphs = [];
        let ttsHideTimeout = null;
        let isTTSPlaying = false;
        let isTTSPaused = false;

        // 初始化TTS
        function initTTS() {
            if ('speechSynthesis' in window) {
                isTTSEnabled = true;
                loadVoices();
                speechSynthesis.onvoiceschanged = loadVoices;
                ttsSpeedDisplay.textContent = ttsRate.toFixed(1);
                showTTSIndicator('语音朗读功能已就绪');
            } else {
                isTTSEnabled = false;
                ttsToggleBtn.style.display = 'none';
                showTTSIndicator('您的浏览器不支持语音朗读功能', true);
            }
        }

        // 加载可用语音
        function loadVoices() {
            ttsVoices = speechSynthesis.getVoices();
            ttsVoiceSelect.innerHTML = '<option value="">选择语音...</option>';
            
            const chineseVoices = ttsVoices.filter(voice => 
                voice.lang.includes('zh') || voice.lang.includes('cn')
            );
            
            const otherVoices = ttsVoices.filter(voice => 
                !voice.lang.includes('zh') && !voice.lang.includes('cn')
            );
            
            chineseVoices.forEach(voice => {
                const option = document.createElement('option');
                option.value = voice.voiceURI;
                option.textContent = `${voice.name} (${voice.lang})`;
                option.selected = voice.voiceURI === ttsVoiceURI;
                ttsVoiceSelect.appendChild(option);
            });
            
            if (chineseVoices.length > 0 && otherVoices.length > 0) {
                const separator = document.createElement('option');
                separator.disabled = true;
                separator.textContent = '──────────';
                ttsVoiceSelect.appendChild(separator);
            }
            
            otherVoices.forEach(voice => {
                const option = document.createElement('option');
                option.value = voice.voiceURI;
                option.textContent = `${voice.name} (${voice.lang})`;
                option.selected = voice.voiceURI === ttsVoiceURI;
                ttsVoiceSelect.appendChild(option);
            });
            
            if (!ttsVoiceURI && chineseVoices.length > 0) {
                ttsVoiceURI = chineseVoices[0].voiceURI;
                ttsVoiceSelect.value = ttsVoiceURI;
                localStorage.setItem('ttsVoiceURI', ttsVoiceURI);
            }
        }

        // 显示TTS指示器
        function showTTSIndicator(message, isError = false) {
            ttsIndicator.textContent = message;
            ttsIndicator.style.background = isError ? 'var(--accent-color)' : 'var(--secondary-color)';
            ttsIndicator.classList.add('show');
            setTimeout(() => {
                ttsIndicator.classList.remove('show');
            }, 2000);
        }

        // 准备朗读文本
        function prepareTextForTTS(scope = 'chapter') {
            const content = document.getElementById('chapterContent');
            paragraphs = Array.from(content.querySelectorAll('p')).filter(p => p.textContent.trim().length > 0);
            
            if (paragraphs.length === 0) {
                showTTSIndicator('没有找到可朗读的文本', true);
                return false;
            }
            
            if (scope === 'current') {
                const viewportMiddle = window.innerHeight / 2;
                let currentIndex = 0;
                
                for (let i = 0; i < paragraphs.length; i++) {
                    const rect = paragraphs[i].getBoundingClientRect();
                    if (rect.top <= viewportMiddle && rect.bottom >= viewportMiddle) {
                        currentIndex = i;
                        break;
                    }
                }
                
                currentParagraphIndex = currentIndex;
            } else {
                currentParagraphIndex = 0;
            }
            
            return true;
        }

        // 开始朗读
        function startTTS() {
            if (!isTTSEnabled) {
                showTTSIndicator('语音朗读功能不可用', true);
                return;
            }
            
            if (currentParagraphIndex >= paragraphs.length) {
                showTTSIndicator('朗读完成');
                stopTTS();
                return;
            }
            
            if (speechSynthesis.speaking) {
                speechSynthesis.cancel();
            }
            
            const paragraph = paragraphs[currentParagraphIndex];
            const text = paragraph.textContent.trim();
            
            if (!text) {
                currentParagraphIndex++;
                setTimeout(startTTS, 100);
                return;
            }
            
            isTTSActive = true;
            
            document.querySelectorAll('.tts-highlight').forEach(el => {
                el.classList.remove('tts-highlight');
            });
            
            paragraph.classList.add('tts-highlight');
            
            isProgrammaticScroll = true;
            paragraph.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
            setTimeout(() => { isProgrammaticScroll = false; }, 500);
            
            currentUtterance = new SpeechSynthesisUtterance(text);
            currentUtterance.rate = ttsRate;
            currentUtterance.pitch = 1.0;
            currentUtterance.volume = 1.0;
            
            if (ttsVoiceURI) {
                const selectedVoice = ttsVoices.find(voice => voice.voiceURI === ttsVoiceURI);
                if (selectedVoice) {
                    currentUtterance.voice = selectedVoice;
                }
            }
            
            currentUtterance.onend = function(event) {
                paragraph.classList.remove('tts-highlight');
                currentParagraphIndex++;
                
                if (currentParagraphIndex < paragraphs.length && isTTSPlaying && !isTTSPaused) {
                    setTimeout(() => {
                        if (isTTSPlaying && !isTTSPaused && currentParagraphIndex < paragraphs.length) {
                            startTTS();
                        }
                    }, 300);
                } else if (currentParagraphIndex >= paragraphs.length) {
                    showTTSIndicator('朗读完成');
                    stopTTS();
                }
            };
            
            currentUtterance.onerror = function(event) {
                console.error('TTS Error:', event);
                paragraph.classList.remove('tts-highlight');
                
                if (event.error === 'interrupted') {
                    console.log('朗读被中断');
                } else {
                    showTTSIndicator('朗读出错: ' + event.error, true);
                    currentParagraphIndex++;
                    if (isTTSPlaying && !isTTSPaused && currentParagraphIndex < paragraphs.length) {
                        setTimeout(startTTS, 500);
                    }
                }
            };
            
            try {
                speechSynthesis.speak(currentUtterance);
                isTTSPlaying = true;
                isTTSPaused = false;
                ttsPlayBtn.style.display = 'none';
                ttsPauseBtn.style.display = 'flex';
                ttsControlPanel.classList.add('hidden');
                showTTSIndicator(`朗读中... (${currentParagraphIndex + 1}/${paragraphs.length})`);
            } catch (error) {
                console.error('TTS Speak Error:', error);
                showTTSIndicator('朗读启动失败', true);
                currentParagraphIndex++;
                if (isTTSPlaying && !isTTSPaused && currentParagraphIndex < paragraphs.length) {
                    setTimeout(startTTS, 500);
                }
            }
        }

        // 暂停朗读
        function pauseTTS() {
            if (speechSynthesis.speaking && !speechSynthesis.paused) {
                speechSynthesis.pause();
                isTTSPaused = true;
                ttsPlayBtn.style.display = 'flex';
                ttsPauseBtn.style.display = 'none';
                showTTSIndicator('已暂停');
            }
        }

        // 继续朗读
        function resumeTTS() {
            if (speechSynthesis.speaking && speechSynthesis.paused) {
                speechSynthesis.resume();
                isTTSPaused = false;
                ttsPlayBtn.style.display = 'none';
                ttsPauseBtn.style.display = 'flex';
                showTTSIndicator('继续朗读');
            } else if (!speechSynthesis.speaking && isTTSPlaying) {
                startTTS();
            }
        }

        // 停止朗读
        function stopTTS() {
            speechSynthesis.cancel();
            isTTSPlaying = false;
            isTTSPaused = false;
            isTTSActive = false;
            currentParagraphIndex = 0;
            
            document.querySelectorAll('.tts-highlight').forEach(el => {
                el.classList.remove('tts-highlight');
            });
            
            ttsPlayBtn.style.display = 'flex';
            ttsPauseBtn.style.display = 'none';
            
            showTTSIndicator('朗读已停止');
        }

        // 调整语速
        function changeTTSRate(delta) {
            ttsRate = Math.max(0.5, Math.min(2.0, ttsRate + delta));
            ttsSpeedDisplay.textContent = ttsRate.toFixed(1);
            localStorage.setItem('ttsRate', ttsRate.toString());
            
            if (speechSynthesis.speaking) {
                const wasPlaying = isTTSPlaying && !isTTSPaused;
                const currentIndex = currentParagraphIndex;
                stopTTS();
                if (wasPlaying) {
                    currentParagraphIndex = currentIndex;
                    setTimeout(() => {
                        if (paragraphs.length > 0) {
                            startTTS();
                        }
                    }, 300);
                }
            }
        }

        // TTS面板显示控制
        function showTTSPanel() {
            if (ttsHideTimeout) {
                clearTimeout(ttsHideTimeout);
            }
            
            ttsControlPanel.classList.remove('hidden');
            
            ttsHideTimeout = setTimeout(() => {
                ttsControlPanel.classList.add('hidden');
            }, 5000);
        }

        // TTS事件绑定
        ttsToggleBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            
            if (ttsControlPanel.classList.contains('hidden')) {
                showTTSPanel();
            } else {
                ttsControlPanel.classList.add('hidden');
            }
        });

        ttsPlayBtn.addEventListener('click', function() {
            if (speechSynthesis.paused) {
                resumeTTS();
            } else {
                if (prepareTextForTTS('chapter')) {
                    startTTS();
                }
            }
        });

        ttsPauseBtn.addEventListener('click', pauseTTS);
        ttsStopBtn.addEventListener('click', stopTTS);

        ttsSpeedDownBtn.addEventListener('click', () => changeTTSRate(-0.1));
        ttsSpeedUpBtn.addEventListener('click', () => changeTTSRate(0.1));

        ttsVoiceSelect.addEventListener('change', function() {
            ttsVoiceURI = this.value;
            localStorage.setItem('ttsVoiceURI', ttsVoiceURI);
            
            if (speechSynthesis.speaking) {
                const wasPlaying = isTTSPlaying && !isTTSPaused;
                const currentIndex = currentParagraphIndex;
                stopTTS();
                if (wasPlaying) {
                    currentParagraphIndex = currentIndex;
                    setTimeout(() => {
                        if (paragraphs.length > 0) {
                            startTTS();
                        }
                    }, 300);
                }
            }
        });

        ttsCurrentBtn.addEventListener('click', function() {
            if (prepareTextForTTS('current')) {
                startTTS();
            }
        });

        ttsChapterBtn.addEventListener('click', function() {
            if (prepareTextForTTS('chapter')) {
                startTTS();
            }
        });

        // TTS面板鼠标交互
        ttsControlPanel.addEventListener('mouseenter', function() {
            if (ttsHideTimeout) {
                clearTimeout(ttsHideTimeout);
            }
        });

        ttsControlPanel.addEventListener('mouseleave', function() {
            ttsHideTimeout = setTimeout(() => {
                ttsControlPanel.classList.add('hidden');
            }, 2000);
        });

        // 页面卸载时停止朗读
        window.addEventListener('beforeunload', stopTTS);
        window.addEventListener('pagehide', stopTTS);
        
        // 章节加载功能
        let index = <?php echo $index; ?>;
        let file = "<?php echo urlencode($file); ?>";
        let loading = false;
        let scrollThreshold = 100;

        const checkScroll = debounce(() => {
            if (loading) return;

            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const scrollHeight = document.documentElement.scrollHeight;
            const clientHeight = window.innerHeight;
            
            if (scrollTop + clientHeight >= scrollHeight - scrollThreshold) {
                loading = true;
                loadNextChapter();
            }
        }, 100);

        window.addEventListener('scroll', checkScroll, { passive: true });

        function loadNextChapter() {
            document.getElementById('loading').style.display = 'block';

            // 保持当前阅读格式
            const formatParam = `&format=${currentFormat}`;
            
            fetch(`chapter.php?index=${index + 1}&file=${file}${formatParam}`)
                .then(response => response.text())
                .then(data => {
                    let parser = new DOMParser();
                    let doc = parser.parseFromString(data, 'text/html');
                    let nextChapterContent = doc.querySelector('.chapter-content');
                    let nextChapterTitle = doc.querySelector('.header h1');

                    if (nextChapterContent && nextChapterContent.textContent.trim() !== '') {
                        const divider = document.createElement('hr');
                        divider.className = 'chapter-divider';
                        document.getElementById('chapterContent').appendChild(divider);
                        
                        if (nextChapterTitle) {
                            const newTitle = document.createElement('h2');
                            newTitle.textContent = nextChapterTitle.textContent;
                            newTitle.style.textAlign = 'center';
                            newTitle.style.marginTop = '20px';
                            newTitle.style.marginBottom = '15px';
                            newTitle.style.fontSize = '1.3rem';
                            newTitle.style.color = 'var(--primary-color)';
                            document.getElementById('chapterContent').appendChild(newTitle);
                        }
                        
                        const newContent = document.createElement('div');
                        newContent.innerHTML = nextChapterContent.innerHTML;
                        document.getElementById('chapterContent').appendChild(newContent);
                        
                        index++;
                        
                        if (nextChapterTitle) {
                            document.title = "<?php echo htmlspecialchars($novelTitle); ?> - " + nextChapterTitle.textContent;
                        }
                    } else {
                        if (index > 0) {
                            setTimeout(() => {
                                alert("已读完所有章节");
                            }, 500);
                        }
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert("加载失败，请检查网络连接");
                })
                .finally(() => {
                    loading = false;
                    document.getElementById('loading').style.display = 'none';
                });
        }
        
        <?php endif; ?>
        
        // ========== 其他原有功能 ==========
        
        // 字体大小控制
        const fontSizeBtn = document.getElementById('font-size-btn');
        const fontIndicator = document.getElementById('fontIndicator');
        const body = document.body;
        
        const fontSizes = [
            { class: 'font-small', name: '小' },
            { class: 'font-medium', name: '中' },
            { class: 'font-large', name: '大' },
            { class: 'font-xlarge', name: '特大' }
        ];
        
        let currentFontSize = parseInt(localStorage.getItem('preferredFontSize')) || 1;
        
        function initFontSize() {
            fontSizes.forEach(size => {
                body.classList.remove(size.class);
            });
            body.classList.add(fontSizes[currentFontSize].class);
        }
        
        function showFontIndicator() {
            if (fontIndicator) {
                fontIndicator.textContent = `字体大小: ${fontSizes[currentFontSize].name}`;
                fontIndicator.classList.add('show');
                setTimeout(() => {
                    fontIndicator.classList.remove('show');
                }, 1500);
            }
        }
        
        if (fontSizeBtn) {
            fontSizeBtn.addEventListener('click', function() {
                currentFontSize = (currentFontSize + 1) % fontSizes.length;
                initFontSize();
                showFontIndicator();
                localStorage.setItem('preferredFontSize', currentFontSize);
            });
        }
        
        // 夜间模式切换
        const darkModeBtn = document.getElementById('dark-mode-btn');
        
        function initDarkMode() {
            const darkMode = localStorage.getItem('darkMode');
            if (darkMode === 'enabled') {
                document.body.classList.add('dark-mode');
                const icon = darkModeBtn.querySelector('i');
                icon.classList.remove('fa-moon');
                icon.classList.add('fa-sun');
            }
        }
        
        if (darkModeBtn) {
            darkModeBtn.addEventListener('click', function() {
                document.body.classList.toggle('dark-mode');
                const icon = darkModeBtn.querySelector('i');
                if (document.body.classList.contains('dark-mode')) {
                    icon.classList.remove('fa-moon');
                    icon.classList.add('fa-sun');
                    localStorage.setItem('darkMode', 'enabled');
                } else {
                    icon.classList.remove('fa-sun');
                    icon.classList.add('fa-moon');
                    localStorage.setItem('darkMode', 'disabled');
                }
            });
        }
        
        // 防抖函数
        function debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
        
        // 初始化所有设置
        window.addEventListener('load', function() {
            <?php if ($fileType === 'text'): ?>
            initReadingFormat();
            initScrollSpeed();
            initTTS();
            resetHidePanelTimeout();
            <?php endif; ?>
            initFontSize();
            initDarkMode();
            document.body.style.minHeight = window.innerHeight + 'px';
        });

        // 尽早恢复阅读格式
        document.addEventListener('DOMContentLoaded', function() {
            <?php if ($fileType === 'text'): ?>
            // 立即尝试从本地存储恢复阅读格式
            const savedFormat = localStorage.getItem('preferredReadingFormat');
            if (savedFormat && savedFormat !== currentFormat) {
                applyFormat(savedFormat);
                console.log('DOMContentLoaded: 从本地存储恢复格式:', savedFormat);
            }
            <?php endif; ?>
        });

        // 添加触摸事件支持
        document.addEventListener('touchstart', function() {}, { passive: true });
        
        // 键盘导航支持
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                const formatPickerModal = document.getElementById('formatPickerModal');
                if (formatPickerModal && formatPickerModal.classList.contains('show')) {
                    formatPickerModal.classList.remove('show');
                }
            }
        });
    </script>
</body>
</html>