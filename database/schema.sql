-- ============================================================
-- B站数据库建表语句 - 简洁实用版
-- 作者: 数仓工程师 & 数据分析师
-- 日期: 2026-02-13
-- 说明: 三表通过 bvid 关联，支持视频数据的完整分析
-- ============================================================

SET NAMES utf8mb4;

-- ============================================================
-- 1. 视频表 (bilibili_videos)
-- 对应文件: bilibili_videos.json
-- 核心主表，存储视频基础信息和统计数据
-- ============================================================
DROP TABLE IF EXISTS `bilibili_videos`;
CREATE TABLE `bilibili_videos` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `bvid` VARCHAR(20) NOT NULL COMMENT 'BV号(关联键)',
  `aid` BIGINT UNSIGNED NOT NULL COMMENT 'AV号',
  `title` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '视频标题',
  `desc` TEXT COMMENT '视频简介',
  `duration` INT UNSIGNED DEFAULT 0 COMMENT '视频时长(秒)',
  
  -- 统计数据
  `view` INT UNSIGNED DEFAULT 0 COMMENT '播放量',
  `danmaku` INT UNSIGNED DEFAULT 0 COMMENT '弹幕数',
  `reply` INT UNSIGNED DEFAULT 0 COMMENT '评论数',
  `favorite` INT UNSIGNED DEFAULT 0 COMMENT '收藏数',
  `coin` INT UNSIGNED DEFAULT 0 COMMENT '投币数',
  `share` INT UNSIGNED DEFAULT 0 COMMENT '分享数',
  `like` INT UNSIGNED DEFAULT 0 COMMENT '点赞数',
  
  -- UP主信息
  `owner_mid` BIGINT UNSIGNED NOT NULL COMMENT 'UP主MID',
  `owner_name` VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'UP主昵称',
  `owner_face` VARCHAR(500) DEFAULT '' COMMENT 'UP主头像URL',
  
  -- 其他信息
  `pic` VARCHAR(500) DEFAULT '' COMMENT '视频封面URL',
  `pubdate` BIGINT UNSIGNED DEFAULT 0 COMMENT '发布时间戳',
  `ctime` BIGINT UNSIGNED DEFAULT 0 COMMENT '创建时间戳',
  
  -- 爬取信息
  `created_time` DATETIME NOT NULL COMMENT '数据采集时间',
  `last_modify_ts` BIGINT UNSIGNED DEFAULT 0 COMMENT '最后修改时间戳',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_bvid_created` (`bvid`, `created_time`), -- 同一视频可以多次爬取
  KEY `idx_owner_mid` (`owner_mid`),
  KEY `idx_view` (`view`),
  KEY `idx_created_time` (`created_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='B站视频数据表';

-- ============================================================
-- 2. 评论表 (bilibili_comments)
-- 对应文件: bilibili_comments_{bvid}.json
-- 存储视频评论数据，通过 bvid 关联到视频表
-- ============================================================
DROP TABLE IF EXISTS `bilibili_comments`;
CREATE TABLE `bilibili_comments` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `bvid` VARCHAR(20) NOT NULL COMMENT 'BV号(关联键，关联到视频表)',
  `rpid` BIGINT UNSIGNED NOT NULL COMMENT '评论ID',
  `oid` BIGINT UNSIGNED NOT NULL COMMENT '对象ID(视频AID)',
  `type` TINYINT UNSIGNED DEFAULT 1 COMMENT '评论类型',
  
  -- 评论者信息
  `mid` BIGINT UNSIGNED NOT NULL COMMENT '评论者MID',
  `uname` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '评论者昵称',
  
  -- 评论内容
  `message` TEXT NOT NULL COMMENT '评论内容',
  `like` INT UNSIGNED DEFAULT 0 COMMENT '点赞数',
  `reply_count` INT UNSIGNED DEFAULT 0 COMMENT '回复数',
  
  -- 时间信息
  `ctime` BIGINT UNSIGNED NOT NULL COMMENT '评论时间戳',
  `last_modify_ts` BIGINT UNSIGNED DEFAULT 0 COMMENT '最后修改时间戳',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_rpid` (`rpid`),
  KEY `idx_bvid` (`bvid`), -- 关联索引：查询某个视频的所有评论
  KEY `idx_oid` (`oid`),
  KEY `idx_mid` (`mid`),
  KEY `idx_ctime` (`ctime`),
  KEY `idx_like` (`like`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='B站评论数据表';

-- ============================================================
-- 3. 弹幕表 (bilibili_danmaku)
-- 对应文件: bilibili_danmaku_{bvid}.json
-- 存储视频弹幕数据，通过 bvid 关联到视频表
-- ============================================================
DROP TABLE IF EXISTS `bilibili_danmaku`;
CREATE TABLE `bilibili_danmaku` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `bvid` VARCHAR(20) NOT NULL COMMENT 'BV号(关联键，关联到视频表)',
  `row_id` VARCHAR(50) NOT NULL COMMENT 'B站弹幕数据库ID',
  
  -- 弹幕内容
  `text` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '弹幕内容',
  `time` DECIMAL(10,3) NOT NULL COMMENT '弹幕在视频中的时间点(秒)',
  
  -- 弹幕属性
  `mode` TINYINT UNSIGNED DEFAULT 1 COMMENT '弹幕模式',
  `size` TINYINT UNSIGNED DEFAULT 25 COMMENT '字体大小',
  `color` INT UNSIGNED DEFAULT 16777215 COMMENT '颜色',
  `timestamp` BIGINT UNSIGNED NOT NULL COMMENT '发送时间戳',
  `pool` TINYINT UNSIGNED DEFAULT 0 COMMENT '弹幕池',
  `user_id` VARCHAR(20) DEFAULT '' COMMENT '用户ID哈希',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_row_id` (`row_id`),
  KEY `idx_bvid` (`bvid`), -- 关联索引：查询某个视频的所有弹幕
  KEY `idx_time` (`time`),
  KEY `idx_timestamp` (`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='B站弹幕数据表';

-- ============================================================
-- 常用分析查询示例（已修复，使用 bvid 关联）
-- ============================================================

-- 1. 查看最新爬取的视频
-- SELECT bvid, title, view, like, created_time 
-- FROM bilibili_videos 
-- ORDER BY created_time DESC 
-- LIMIT 10;

-- 2. 查看某个视频的播放量增长趋势
-- SELECT created_time, view, like, coin 
-- FROM bilibili_videos 
-- WHERE bvid = 'BV1A3cczZEf6' 
-- ORDER BY created_time;

-- 3. 查看某视频的评论（通过 bvid 关联）
-- SELECT c.uname, c.message, c.like, FROM_UNIXTIME(c.ctime) AS comment_time 
-- FROM bilibili_comments c
-- WHERE c.bvid = 'BV1A3cczZEf6' 
-- ORDER BY c.like DESC 
-- LIMIT 20;

-- 4. 查看某视频的高能时刻（弹幕密集的时间段，通过 bvid 关联）
-- SELECT FLOOR(d.time / 10) * 10 AS time_segment, COUNT(*) AS danmaku_count 
-- FROM bilibili_danmaku d
-- WHERE d.bvid = 'BV1A3cczZEf6'
-- GROUP BY time_segment 
-- ORDER BY danmaku_count DESC 
-- LIMIT 10;

-- 5. 综合分析：视频的基本数据 + 评论数 + 弹幕数（JOIN 查询）
-- SELECT 
--   v.bvid,
--   v.title,
--   v.view,
--   v.like,
--   COUNT(DISTINCT c.rpid) AS comment_count,
--   COUNT(DISTINCT d.row_id) AS danmaku_count
-- FROM bilibili_videos v
-- LEFT JOIN bilibili_comments c ON v.bvid = c.bvid
-- LEFT JOIN bilibili_danmaku d ON v.bvid = d.bvid
-- WHERE v.bvid = 'BV1A3cczZEf6'
-- GROUP BY v.bvid, v.title, v.view, v.like;

-- 6. UP主视频数据汇总（影视飓风）
-- SELECT 
--   v.owner_name,
--   COUNT(DISTINCT v.bvid) AS video_count,
--   SUM(v.view) AS total_view,
--   SUM(v.like) AS total_like,
--   AVG(v.view) AS avg_view
-- FROM bilibili_videos v
-- WHERE v.owner_mid = 436482484
-- GROUP BY v.owner_name;
